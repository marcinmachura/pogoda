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


// computes dominant (aka most popular) climate classification for given dataset
// m = number of years need to be agregated for basic metrics
// n = lenght of final aggeration (dominant-search) window
let writeClassificationsCsvDominant (bm: BinaryModel.BinaryModel) (outPath: string) (m:int) (n:int): unit =
    if n <= 0 then invalidArg "n" "aggregation window n must be >= 1"
    if m <= 0 then invalidArg "m" "aggregation window m must be >= 1"
    use sw = new System.IO.StreamWriter(outPath)
    sw.WriteLine("Lat,Lon,year,koppen,trewartha")
    let mutable rowCount = 0L
    let aggregated = 
        classifyAllLocations bm m
        |> Seq.map (fun (lat, lon,year, climate,_) -> (lat,lon,year, climate)) 
        |> Seq.groupBy (fun (lat, lon,_, _) -> (lat,lon)) 
        |> Seq.map (fun (key, values) ->
            let innerMap = 
                values 
                |> Seq.map (fun (_,_,year, climate) -> (year, climate))
                |> Array.ofSeq 
                |> Array.sortBy (fun (year,_)->year)
            (key, innerMap)
        )
        |> dict
    for lat,lon in aggregated.Keys do
        let data = aggregated[lat,lon]
        for year = 0+n to data.Length - 1 do
            let dominantClimate = 
                Array.sub data (year-n) n
                |> Seq.ofArray 
                |> Seq.map (fun (_,climate) -> climate) 
                |> Seq.groupBy id 
                |> Seq.map (fun (climate, duplicates) -> (climate, Seq.length duplicates))
                |> Seq.maxBy (fun (climate, freq) -> freq)
                |> fst
            sw.WriteLine(sprintf "%.6f,%.6f,%d,%s,%s" lat lon (fst data[year]) dominantClimate "N/A")
    sw.Flush()

