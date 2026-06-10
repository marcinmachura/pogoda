module ClimateReader

open System
open System.IO
open System.Text.Json
open System.Text.RegularExpressions
open System.Collections.Generic
open ClimateClassifier

// ClimateRecord moved to ClimateClassifier.fs

/// Encode latitude and longitude into a single int64 using the same scheme as convert_pq2json.py
let encodeCoordinates (lat: float) (lon: float) : int64 =
    let latSign = if lat >= 0.0 then 0L else 1L
    let lonSign = if lon >= 0.0 then 0L else 1L
    let latAbs = int64 (Math.Abs(lat) * 100000.0)
    let lonAbs = int64 (Math.Abs(lon) * 100000.0)
    // Format: [lat_sign][lat_7digits][lon_sign][lon_8digits]
    latSign * 100000000000000000L + latAbs * 1000000000L + lonSign * 100000000L + lonAbs

/// Decode int64 back into (lat, lon) floats (approximate original values)
let decodeCoordinates (code: int64) : float * float =
    let A = 100000000000000000L
    let B = 1000000000L
    let C = 100000000L
    let latSign = code / A
    let rem = code % A
    let latAbs = rem / B
    let rem2 = rem % B
    let lonSign = rem2 / C
    let lonAbs = rem2 % C
    let lat = (float latAbs) / 100000.0
    let lon = (float lonAbs) / 100000.0
    let lat = if latSign = 0L then lat else -lat
    let lon = if lonSign = 0L then lon else -lon
    (lat, lon)

/// Haversine distance between two lat/lon points in kilometers
let private haversineKm (lat1: float) (lon1: float) (lat2: float) (lon2: float) : float =
    let toRad x = x * System.Math.PI / 180.0
    let r = 6371.0
    let dLat = toRad (lat2 - lat1)
    let dLon = toRad (lon2 - lon1)
    let a = System.Math.Sin(dLat/2.0) ** 2.0 + System.Math.Cos(toRad lat1) * System.Math.Cos(toRad lat2) * (System.Math.Sin(dLon/2.0) ** 2.0)
    let c = 2.0 * System.Math.Atan2(System.Math.Sqrt(a), System.Math.Sqrt(1.0 - a))
    r * c

/// Find nearest coordinate key in compact dictionary to given lat/lon and print it with distance (km)
let findNearest (compact: Dictionary<int64, Dictionary<int, (int16 list * int16 list)>>) (lat: float) (lon: float) : (int64 * float) option =
    if compact.Count = 0 then
        printfn "No data in compact structure"
        None
    else
        let mutable bestKey = 0L
        let mutable bestDist = System.Double.PositiveInfinity
        for key in compact.Keys do
            let (plat, plon) = decodeCoordinates key
            let d = haversineKm lat lon plat plon
            if d < bestDist then
                bestDist <- d
                bestKey <- key
        let (blat, blon) = decodeCoordinates bestKey
        printfn "Nearest data point: coord=%d -> lat=%.6f lon=%.6f distance=%.3f km" bestKey blat blon bestDist
        Some(bestKey, bestDist)




let private clampIntToInt16 (v: int) : int16 =
    let maxv = int System.Int16.MaxValue
    let minv = int System.Int16.MinValue
    if v > maxv then System.Int16.MaxValue
    elif v < minv then System.Int16.MinValue
    else int16 v

let private floatToTempInt16 (f: float) : int16 =
    // multiply by 100 and round (same semantics as the Python version)
    let iv = int (Math.Round(f * 100.0))
    clampIntToInt16 iv

let private floatToPrecipInt16 (f: float) : int16 =
    // multiply by 10 and round
    let iv = int (Math.Round(f * 10.0))
    clampIntToInt16 iv

/// Convert parsed records into compact in-memory structure:
/// Map<coord:int64, Map<year:int, (temps:int16 list, precs:int16 list)>>
let convertToCompact (records: seq<ClimateRecord>) : Dictionary<int64, Dictionary<int, (int16 list * int16 list)>> =
    let outer = Dictionary<int64, Dictionary<int, (ResizeArray<int16> * ResizeArray<int16>)>>()

    for r in records do
        let coord = encodeCoordinates r.Lat r.Lon
        let inner =
            match outer.TryGetValue(coord) with
            | true, d -> d
            | false, _ ->
                let d = Dictionary<int, (ResizeArray<int16> * ResizeArray<int16>)>()
                outer.[coord] <- d
                d

        for kv in r.Climate do
            // year keys may be strings; try parse to int
            match System.Int32.TryParse(kv.Key) with
            | true, year ->
                let pairs = kv.Value
                // Expect 12 monthly pairs
                if List.length pairs = 12 then
                    let temps = ResizeArray<int16>()
                    let precs = ResizeArray<int16>()
                    for (t, p) in pairs do
                        temps.Add(floatToTempInt16 t)
                        precs.Add(floatToPrecipInt16 p)
                    inner.[year] <- (temps, precs)
                else
                    () // skip incomplete years
            | false, _ -> ()

    // Convert inner ResizeArrays to immutable lists and return nested Dictionaries
    let result = Dictionary<int64, Dictionary<int, (int16 list * int16 list)>>()
    for kvp in outer do
        let coord = kvp.Key
        let yearsDict = kvp.Value
        let inner = Dictionary<int, (int16 list * int16 list)>()
        for ykv in yearsDict do
            let y = ykv.Key
            let (ta, pa) = ykv.Value
            let tlist = Seq.toList ta
            let plist = Seq.toList pa
            inner.Add(y, (tlist, plist))
        result.Add(coord, inner)
    result

let private tryParseJson (s: string) : Result<Dictionary<string, (float * float) list>, string> =
    try
        use doc = JsonDocument.Parse(s)
        let root = doc.RootElement
        if root.ValueKind <> JsonValueKind.Object then Error "root is not an object"
        else
            let dict = Dictionary<string, (float * float) list>()
            for prop in root.EnumerateObject() do
                let elem = prop.Value
                if elem.ValueKind <> JsonValueKind.Array then raise (FormatException(sprintf "Property %s: expected array of pairs" prop.Name))
                let parsed =
                    elem.EnumerateArray()
                    |> Seq.map (fun item ->
                        if item.ValueKind = JsonValueKind.Array then
                            let arr = item.EnumerateArray() |> Seq.toArray
                            if arr.Length >= 2 then
                                try
                                    let t = arr.[0].GetDouble()
                                    let p = arr.[1].GetDouble()
                                    Ok (t, p)
                                with ex -> Error (sprintf "number parse error: %s" ex.Message)
                            else Error "pair length < 2"
                        else Error "pair is not an array")
                    |> Seq.fold (fun acc r ->
                        match acc, r with
                        | Ok l, Ok v -> Ok (v :: l)
                        | Error e, _ -> Error e
                        | _, Error e -> Error e) (Ok [])
                match parsed with
                | Ok l -> dict.Add(prop.Name, List.rev l)
                | Error e -> raise (FormatException(sprintf "Property %s: %s" prop.Name e))
            Ok dict
    with ex -> Error ex.Message

let private transformPythonLike (s: string) : string =
    // Convert common Python-ish syntax to JSON-ish syntax
    // - single quotes -> double quotes
    // - tuples ( ... ) -> arrays [ ... ]
    // - numeric keys like {1990: ...} -> {"1990": ...}
    let t1 = s.Replace("'", "\"").Replace("(", "[").Replace(")", "]")
    let pattern = "(?<=\{|,)\s*([0-9]+)\s*:"
    Regex.Replace(t1, pattern, fun (m: Match) -> sprintf "\"%s\":" m.Groups.[1].Value)

let parseClimateField (s: string) : Dictionary<string, (float * float) list> =
    let trimmed = s.Trim()
    if String.IsNullOrEmpty(trimmed) then Dictionary<string, (float * float) list>()
    else
        match tryParseJson trimmed with
        | Ok m -> m
        | Error _ ->
            let transformed = transformPythonLike trimmed
            match tryParseJson transformed with
            | Ok m -> m
            | Error e -> failwithf "Failed to parse climate field. Tried JSON and transformed JSON. Error: %s\nTransformed text: %s" e transformed

let readClimateTsv (path: string) : seq<ClimateRecord> =
    if not (File.Exists path) then raise (FileNotFoundException(sprintf "File not found: %s" path))
    seq {
        use lines = File.OpenText(path)
        let mutable lineno = 0
        while not lines.EndOfStream do
            let raw = lines.ReadLine()
            lineno <- lineno + 1
            if not (String.IsNullOrWhiteSpace raw) && not (raw.TrimStart().StartsWith("#")) then
                let parts = raw.Split([| '\t' |], 3)
                if parts.Length < 3 then raise (FormatException(sprintf "Line %d: expected at least 3 tab-separated fields" lineno))
                let lat = Double.Parse(parts.[0], System.Globalization.CultureInfo.InvariantCulture)
                let lon = Double.Parse(parts.[1], System.Globalization.CultureInfo.InvariantCulture)
                let climate = parseClimateField(parts.[2])
                yield { Lat = lat; Lon = lon; Climate = climate }
    }


// --- Decoding helpers ---

type DecodedLocation = { Coord: int64; Years: Dictionary<int, (float[] * float[])> }

/// Decode a compact dictionary entry (int16-encoded temps/precips) for a given coordinate.
let decodeCompact (compact: Dictionary<int64, Dictionary<int, (int16 list * int16 list)>>) (coord: int64) : DecodedLocation option =
    if not (compact.ContainsKey(coord)) then None
    else
        let yearsDict = compact.[coord]
        let out = Dictionary<int, (float[] * float[])>()
        for kv in yearsDict do
            let year = kv.Key
            let (tlist, plist) = kv.Value
            // temps were stored as int16 = round(temp * 100)
            let temps = tlist |> Seq.map (fun (v:int16) -> (float v) / 100.0) |> Seq.toArray
            // precips were stored as int16 = round(precip * 10)
            let precs = plist |> Seq.map (fun (v:int16) -> (float v) / 10.0) |> Seq.toArray
            out.Add(year, (temps, precs))
        Some { Coord = coord; Years = out }


/// Write CSV of classifications: Lat:float,Lon:float,year:int,koppen:string,trewartha:string
// writeClassificationsCsv moved to Program.fs
