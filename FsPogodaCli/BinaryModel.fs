module BinaryModel

open System
open System.IO
open System.Collections.Generic
open CompactModel
open ClimateReader

type BinaryModel = {
    Index: Dictionary<uint64, uint32>
    Data: int16[]
}

/// Binary file format reader (same layout as writer used previously)
let loadFromFile (path: string) : BinaryModel =
    use fs = File.OpenRead(path)
    use br = new BinaryReader(fs)
    let a = br.ReadByte()
    let b = br.ReadByte()
    let c = br.ReadByte()
    let d = br.ReadByte()
    if char a <> 'C' || char b <> 'C' || char c <> 'M' || char d <> '1' then failwith "Invalid magic"
    let entryCount = int (br.ReadUInt32())
    let index = Dictionary<uint64, uint32>()
    for i in 0 .. entryCount-1 do
        let key = br.ReadUInt64()
        let idx = br.ReadUInt32()
        index.Add(key, idx)
    let dataLen = int (br.ReadUInt32())
    let data = Array.zeroCreate<int16> dataLen
    for i = 0 to dataLen - 1 do
        data.[i] <- br.ReadInt16()
    { Index = index; Data = data }

/// List available coordinates (decoded lat,lon) from BinaryModel
let listCoords (bm: BinaryModel) : seq<float * float> =
    bm.Index.Keys |> Seq.map (fun k -> decodeCoordinates (int64 k))

/// Find N nearest coordinate keys (int64) to given lat/lon from BinaryModel. Returns sequence of (coordKey:int64, distanceKm:float).
let findNearestN (bm: BinaryModel) (lat: float) (lon: float) (n: int) : seq<int64 * float> =
    let haversineKm (lat1: float) (lon1: float) (lat2: float) (lon2: float) : float =
        let toRad x = x * System.Math.PI / 180.0
        let r = 6371.0
        let dLat = toRad (lat2 - lat1)
        let dLon = toRad (lon2 - lon1)
        let a = System.Math.Sin(dLat/2.0) ** 2.0 + System.Math.Cos(toRad lat1) * System.Math.Cos(toRad lat2) * (System.Math.Sin(dLon/2.0) ** 2.0)
        let c = 2.0 * System.Math.Atan2(System.Math.Sqrt(a), System.Math.Sqrt(1.0 - a))
        r * c

    bm.Index.Keys
    |> Seq.map (fun k -> let (plat, plon) = decodeCoordinates (int64 k) in (int64 k, haversineKm lat lon plat plon))
    |> Seq.sortBy snd
    |> Seq.truncate n

/// Retrieve decoded data for exact lat/lon from BinaryModel
let getForLatLon (bm: BinaryModel) (lat: float) (lon: float) : Dictionary<int, (float[] * float[])> option =
    let key = uint64 (encodeCoordinates lat lon)
    if not (bm.Index.ContainsKey(key)) then None
    else
        let start = int bm.Index.[key]
        let data = bm.Data
        let years = Dictionary<int, (float[] * float[])>()
        let mutable i = start
        let yearCount = int data.[i]
        i <- i + 1
        for _ in 1 .. yearCount do
            let year = int data.[i]
            i <- i + 1
            // read 12 temps
            let temps = Array.init 12 (fun j -> (float data.[i + j]) / 100.0)
            i <- i + 12
            let precs = Array.init 12 (fun j -> (float data.[i + j]) / 10.0)
            i <- i + 12
            years.Add(year, (temps, precs))
        Some years

/// Convert a CompactModel into a BinaryModel (builds index + data array and wraps it)
let ofCompact (cm: CompactModel) : BinaryModel =
    let indexMap, arr = CompactModel.buildIndexAndArray cm
    { Index = indexMap; Data = arr }

/// Save BinaryModel to file (writer)
let saveToFile (path: string) (bm: BinaryModel) : unit =
    use fs = File.Create(path)
    use bw = new BinaryWriter(fs)
    // magic
    bw.Write(byte 'C'); bw.Write(byte 'C'); bw.Write(byte 'M'); bw.Write(byte '1')
    bw.Write(uint32 bm.Index.Count)
    bm.Index |> Seq.cast<KeyValuePair<uint64,uint32>> |> Seq.sortBy (fun kv -> kv.Key) |> Seq.iter (fun kv -> bw.Write(kv.Key); bw.Write(kv.Value))
    bw.Write(uint32 bm.Data.Length)
    for v in bm.Data do bw.Write(v)
    bw.Flush()
