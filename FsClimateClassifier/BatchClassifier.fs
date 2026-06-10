module BatchClassifier

open System
open System.IO
open System.Collections.Generic
open ClimateReader
open ClimateClassifier
open BinaryModel

/// Write CSV of classifications: Lat:float,Lon:float,year:int,koppen:string,trewartha:string
/// n - aggegation window. Just averaging over n years, e.g. n=5 means 2010-2014 for year=2014
/// For a single location's years dictionary, compute the n-year aggregated
/// monthly averages for the window ending at `year` and return the
/// classification codes. Returns None if the window is incomplete or
/// malformed. On classifier failure returns Some(year, "ERROR", "ERROR").
let classifyWindowForYear (years: Dictionary<int, (float[] * float[])>) (year: int) (n: int) (lat: float) : option<int * string * string> =
    if n <= 0 then invalidArg "n" "aggregation window n must be >= 1"
    let startYear = year - n + 1
    // quick presence check
    let yearKeys = years.Keys |> Seq.map id |> Seq.toArray |> Array.sort
    let yearSet = HashSet<int>(yearKeys)
    let mutable haveAll = true
    for yy = startYear to year do if not (yearSet.Contains yy) then haveAll <- false
    if not haveAll then None
    else
        // accumulate sums; if any year's arrays are malformed, skip
        let sumsT = Array.init 12 (fun _ -> 0.0)
        let sumsP = Array.init 12 (fun _ -> 0.0)
        let mutable malformed = false
        for yy = startYear to year do
            match years.TryGetValue(yy) with
            | true, (tarr, parr) when tarr.Length = 12 && parr.Length = 12 ->
                for i = 0 to 11 do
                    sumsT.[i] <- sumsT.[i] + tarr.[i]
                    sumsP.[i] <- sumsP.[i] + parr.[i]
            | _ -> malformed <- true
        if malformed then None
        else
            let avgT = Array.init 12 (fun i -> sumsT.[i] / float n)
            let avgP = Array.init 12 (fun i -> sumsP.[i] / float n)
            try
                let kcode, _ = ClimateClassifier.classify_koppen avgT avgP lat
                let tcode, _ = ClimateClassifier.classify_trewartha avgT avgP lat
                Some (year, kcode, tcode)
            with
            | ClimateClassifier.ClassificationError _ -> Some (year, "ERROR", "ERROR")
            | _ -> Some (year, "ERROR", "ERROR")

/// Iterate over all locations in the binary model and yield classification
/// tuples (lat, lon, year, koppen, trewartha) for the given aggregation window `n`.
let classifyAllLocations (bm: BinaryModel.BinaryModel) (n: int) : seq<float * float * int * string * string> =
    seq {
        for KeyValue(ukey, _idx) in bm.Index do
            let coordKey = int64 ukey
            let (plat, plon) = ClimateReader.decodeCoordinates coordKey
            match BinaryModel.getForLatLon bm plat plon with
            | None -> ()
            | Some years ->
                // iterate sorted years for deterministic output
                let yearKeys = years.Keys |> Seq.map id |> Seq.toArray |> Array.sort
                for year in yearKeys do
                    match classifyWindowForYear years year n plat with
                    | None -> ()
                    | Some (y, k, t) -> yield (plat, plon, y, k, t)
    }

/// Iterate over all locations in the binary model and yield classification
/// tuples (lat, lon, year, koppen, trewartha) for the given aggregation window `n`.
let classifyAllLocationsMedian 
    (bm: BinaryModel.BinaryModel) 
    (m:int) 
    (n: int) : seq<float * float * int * string * string> =
    // seq of (lat, lon, year, value1, value2)
    let foldToNestedMap (data: seq<float * float * int * float * float>) =
        let addEntry (acc: Map<float*float, Map<int, list<float*float>>>) (lat,lon,year,v1,v2) =
            let coord = (lat, lon)
            // inner map for this coordinate (or empty)
            let inner = acc |> Map.tryFind coord |> Option.defaultValue Map.empty
            // existing list for year (prepend new pair)
            let existing = inner |> Map.tryFind year |> Option.defaultValue []
            let updatedInner = inner |> Map.add year ((v1,v2) :: existing)
            acc |> Map.add coord updatedInner
        data |> Seq.fold addEntry Map.empty

    let data = classifyAllLocations bm m

    let data = foldToNestedMap data
    seq {
        for KeyValue(ukey, _idx) in bm.Index do
            let coordKey = int64 ukey
            let (plat, plon) = ClimateReader.decodeCoordinates coordKey
            match BinaryModel.getForLatLon bm plat plon with
            | None -> ()
            | Some years ->
                // iterate sorted years for deterministic output
                let yearKeys = years.Keys |> Seq.map id |> Seq.toArray |> Array.sort
                for year in yearKeys do
                    match classifyWindowForYear years year n plat with
                    | None -> ()
                    | Some (y, k, t) -> yield (plat, plon, y, k, t)
    }

let writeClassificationsCsv (bm: BinaryModel.BinaryModel) (outPath: string) (n:int): unit =
    if n <= 0 then invalidArg "n" "aggregation window n must be >= 1"
    use sw = new System.IO.StreamWriter(outPath)
    sw.WriteLine("Lat,Lon,year,koppen,trewartha")
    let mutable rowCount = 0L
    for (plat, plon, year, kcode, tcode) in classifyAllLocations bm n do
        sw.WriteLine(sprintf "%.6f,%.6f,%d,%s,%s" plat plon year kcode tcode)
        rowCount <- rowCount + 1L
        if rowCount % 100000L = 0L then sw.Flush()
    sw.Flush()


let writeClassificationsCsvMedian (bm: BinaryModel.BinaryModel) (outPath: string) (m:int) (n:int): unit =
    if n <= 0 then invalidArg "n" "aggregation window n must be >= 1"
    // m window aggretation in median preprocessing

    use sw = new System.IO.StreamWriter(outPath)
    sw.WriteLine("Lat,Lon,year,koppen,trewartha")
    let mutable rowCount = 0L
    for (plat, plon, year, kcode, tcode) in classifyAllLocations bm n do
        sw.WriteLine(sprintf "%.6f,%.6f,%d,%s,%s" plat plon year kcode tcode)
        rowCount <- rowCount + 1L
        if rowCount % 100000L = 0L then sw.Flush()
    sw.Flush()

/// Write CSV of classifications: Lat:float,Lon:float,year:int,koppen:string,trewartha:string
/// n - aggegation window. Just averaging over n years, e.g. n=5 means 2010-2014 for year=2014
// v2 should instead of aggeration (average) compute climate data for each year
// btw i can just re use prev with n=1 or n=2
// and the pick median value
// that would be coll
