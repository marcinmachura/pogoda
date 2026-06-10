open System
open System.IO
open System.Diagnostics
open System.Collections.Generic
open CompactModel
open BinaryModel
open BatchClassifier

// writeClassificationsCsv moved to BatchClassifier.fs

let dataFile = @"/home/mmachura/src/my/climateData/climate.tsv"

 // Print a tiny sample from compact
let print_status (compact: Dictionary<int64, Dictionary<int, (int16 list * int16 list)>>) =
    compact |> Seq.truncate 3 |> Seq.iteri (fun i (KeyValue(coord, years)) ->
        let firstYear = if years.Count = 0 then -1 else (years |> Seq.map (fun (KeyValue(y,_)) -> y) |> Seq.head)
        printfn "#%d coord=%d years=%d sampleYear=%d" (i+1) coord years.Count firstYear)

/// Test function that finds nearest point in a BinaryModel and prints classification for 2018
let test_cambridge (bm: BinaryModel) (k: int) =
    let cambridgeLat = 52.2053
    let cambridgeLon = 0.1218
    if bm.Index.Count = 0 then printfn "BinaryModel is empty" else
    let neighbours = BinaryModel.findNearestN bm cambridgeLat cambridgeLon k |> Seq.toArray
    if neighbours.Length = 0 then printfn "No neighbours found" else
    printfn "Top %d nearest neighbours:" neighbours.Length
    for i = 0 to neighbours.Length - 1 do
        let (coordKey, dist) = neighbours.[i]
        let (plat, plon) = ClimateReader.decodeCoordinates coordKey
        printfn "#%d coord=%d lat=%.6f lon=%.6f dist=%.3f km" (i+1) coordKey plat plon dist
        match BinaryModel.getForLatLon bm plat plon with
        | None -> printfn "  (no decoded years available)"
        | Some years ->
            let year = 2018
            if years.ContainsKey(year) then
                let (temps, precs) = years.[year]
                let kcode, _ = ClimateClassifier.classify_koppen temps precs cambridgeLat
                let tcode, _ = ClimateClassifier.classify_trewartha temps precs cambridgeLat
                printfn "  Year %d: Koppen=%s Trewartha=%s" year kcode tcode
            else
                printfn "  Year %d not available" year

// legacy:
// let records = ClimateReader.readClimateTsv dataFile
//let compact = ClimateReader.convertToCompact records
[<EntryPoint>]
let main argv =
    try
        if argv.Length < 2 then
            printfn "Usage: %s OUT_CSV N M " (System.AppDomain.CurrentDomain.FriendlyName)
            printfn "Example: %s /tmp/out.csv 5 1" (System.AppDomain.CurrentDomain.FriendlyName)
            1
        else
            
            let outPath = argv.[0]
            let nStr = argv.[1]
            let mStr = argv.[2]
            let mutable n = 0
            let mutable m = 0

            if not (System.Int32.TryParse(mStr, &m)) then
                printfn "Invalid m value: %s" mStr
                1
            elif not (System.Int32.TryParse(nStr, &n)) then
                printfn "Invalid n value: %s" nStr
                1
            elif n <= 0 then
                printfn "Aggregation window n must be >= 1"
                1
            else
                // Prefer loading binary model from disk; if missing, build and save it
                let outBin = "./compact_climate.bin"
                printfn "n=%i m=%i Loading binary model from %s..." n m outBin
                let bm = BinaryModel.loadFromFile outBin
                printfn "Writing classifications to %s (n=%d)..." outPath n
                BatchClassifier.writeClassificationsCsv bm outPath n // m n for dominat
                printfn "Done."
                0
    with ex ->
        printfn "Error: %s" ex.Message
        1