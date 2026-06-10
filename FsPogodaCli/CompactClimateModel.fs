module CompactModel

open System
open System.Collections.Generic
open ClimateReader

type CompactModel = Dictionary<int64, Dictionary<int, (int16 list * int16 list)>>

/// List available coordinates as sequence of (lat, lon)
let listCoords (cm: CompactModel) : seq<float * float> =
    cm.Keys |> Seq.cast<int64> |> Seq.map (fun k -> decodeCoordinates k)

/// Find N nearest coordinate keys (int64) to given lat/lon. Returns sequence of (coordKey:int64, distanceKm:float) sorted by distance.
let findNearestN (cm: CompactModel) (lat: float) (lon: float) (n: int) : seq<int64 * float> =
    // local haversine helper
    let haversineKm (lat1: float) (lon1: float) (lat2: float) (lon2: float) : float =
        let toRad x = x * System.Math.PI / 180.0
        let r = 6371.0
        let dLat = toRad (lat2 - lat1)
        let dLon = toRad (lon2 - lon1)
        let a = System.Math.Sin(dLat/2.0) ** 2.0 + System.Math.Cos(toRad lat1) * System.Math.Cos(toRad lat2) * (System.Math.Sin(dLon/2.0) ** 2.0)
        let c = 2.0 * System.Math.Atan2(System.Math.Sqrt(a), System.Math.Sqrt(1.0 - a))
        r * c

    cm.Keys
    |> Seq.cast<int64>
    |> Seq.map (fun k -> let (plat, plon) = decodeCoordinates k in (k, haversineKm lat lon plat plon))
    |> Seq.sortBy snd
    |> Seq.truncate n

/// Retrieve decoded data for exact lat/lon (returns dict year -> (temps, precs) with floats)
let getForLatLon (cm: CompactModel) (lat: float) (lon: float) : Dictionary<int, (float[] * float[])> option =
    let key = encodeCoordinates lat lon
    if not (cm.ContainsKey(key)) then None
    else
        let yearsDict = cm.[key]
        let out = Dictionary<int, (float[] * float[])>()
        for KeyValue(y, (tlist, plist)) in yearsDict do
            let temps = tlist |> Seq.map (fun (v:int16) -> (float v) / 100.0) |> Seq.toArray
            let precs = plist |> Seq.map (fun (v:int16) -> (float v) / 10.0) |> Seq.toArray
            out.Add(y, (temps, precs))
        Some out

/// Build a compact binary model (index map + data array) from the in-memory compact dictionary.
/// Returns a map (uint64 -> uint32 startIndex) and the data array (int16[]).
let buildIndexAndArray (compact: CompactModel) : Dictionary<uint64, uint32> * int16[] =
    // We'll iterate coordinates in ascending order for deterministic output
    let keys = compact.Keys |> Seq.cast<int64> |> Seq.sort |> Seq.toArray
    let indexMap = Dictionary<uint64, uint32>()
    let data = ResizeArray<int16>()

    for k in keys do
        let ukey = uint64 k
        // record starting index
        let start = uint32 data.Count
        indexMap.Add(ukey, start)

        let yearsDict = compact.[k]
        // sort years ascending
        let years = yearsDict |> Seq.cast<KeyValuePair<int, (int16 list * int16 list)>> |> Seq.sortBy (fun kv -> kv.Key) |> Seq.toArray
        let yearCount = years.Length
        // number of years as int16
        data.Add(int16 yearCount)
        for ykv in years do
            let year = ykv.Key
            let (tlist, plist) = ykv.Value
            // year as int16
            data.Add(int16 year)
            // temps (already int16 list)
            for t in tlist do data.Add(t)
            // precs
            for p in plist do data.Add(p)

    let arr = data.ToArray()
    (indexMap, arr)

