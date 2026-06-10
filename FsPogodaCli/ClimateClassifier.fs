module ClimateClassifier

open System
open System.Collections.Generic

// Shared record used when reading TSV lines
type ClimateRecord = { Lat: float; Lon: float; Climate: Dictionary<string, (float * float) list> }

let private addDetail (d: Dictionary<string,obj>) key (v: obj) = d.Add(key, v)

exception ClassificationError of string

let classify_trewartha (temps_c: float[]) (precip_mm: float[]) (latitude: float) : string * Dictionary<string,obj> =
    if temps_c.Length <> 12 || precip_mm.Length <> 12 then raise (ClassificationError "Need 12 monthly temperature and precipitation values")

    let annual_mean_temp = Array.sum temps_c / 12.0
    let annual_precip = Array.sum precip_mm
    let warmest = Array.max temps_c
    let coldest = Array.min temps_c
    let m10 = temps_c |> Array.filter (fun t -> t >= 10.0) |> Array.length

    let summer_indices, winter_indices =
        if latitude >= 0.0 then ([|3;4;5;6;7;8|], [|9;10;11;0;1;2|]) else ([|9;10;11;0;1;2|],[|3;4;5;6;7;8|])

    let precip_summer = summer_indices |> Array.sumBy (fun i -> precip_mm.[i])
    let precip_winter = winter_indices |> Array.sumBy (fun i -> precip_mm.[i])
    let summer_precip_percent = if annual_precip > 0.0 then (precip_summer / annual_precip) * 100.0 else 0.0

    // Trewartha arid threshold formula: 10(T - 10) + 3P
    // where T = annual mean temp in °C, P = percentage of precip in high-sun months
    let trewartha_threshold = 10.0 * (annual_mean_temp - 10.0) + 3.0 * summer_precip_percent

    // Universal Thermal Scale for 3rd and 4th letters
    let thermal_letter temp =
        if temp >= 35.0 then "i"
        elif temp >= 28.0 then "h"
        elif temp >= 22.2 then "a"
        elif temp >= 18.0 then "b"
        elif temp >= 10.0 then "l"
        elif temp >= 0.1 then "k"
        elif temp >= -9.9 then "o"
        elif temp >= -24.9 then "c"
        elif temp >= -39.9 then "d"
        else "e"

    // Calculate UTS letters once for all climate groups
    let third_letter = thermal_letter warmest   // UTS for warmest month
    let fourth_letter = thermal_letter coldest  // UTS for coldest month

    let details = Dictionary<string,obj>()
    addDetail details "annual_mean_temp" (box annual_mean_temp)
    addDetail details "annual_precip" (box annual_precip)
    addDetail details "warmest" (box warmest)
    addDetail details "coldest" (box coldest)
    addDetail details "months_ge_10" (box m10)
    addDetail details "precip_summer" (box precip_summer)
    addDetail details "precip_winter" (box precip_winter)
    addDetail details "summer_precip_percent" (box summer_precip_percent)
    addDetail details "trewartha_threshold" (box trewartha_threshold)
    addDetail details "third_letter" (box third_letter)
    addDetail details "fourth_letter" (box fourth_letter)

    // Check for arid climates (Group B)
    if annual_precip < trewartha_threshold then
        let subtype = if annual_precip < (trewartha_threshold / 2.0) then "W" else "S"
        let code = sprintf "B%s%s%s" subtype third_letter fourth_letter
        addDetail details "group" (box "B")
        addDetail details "subtype" (box subtype)
        code, details
    else
        // Determine main climate group
        let group =
            if Array.forall (fun t -> t >= 18.0) temps_c then "A"
            elif m10 >= 8 then "C"
            elif m10 >= 4 && m10 <= 7 then "D"
            elif m10 >= 1 && m10 <= 3 then "E"
            else "F"

        match group with
        | "A" -> // Tropical climates
            let dry_months = precip_mm |> Array.filter (fun p -> p < 60.0) |> Array.length
            let subtype = 
                if dry_months <= 2 then "r"  // wet (≤2 dry months)
                elif dry_months >= 3 then 
                    // Check if dry season is in winter (low-sun) or summer (high-sun)
                    let winter_dry_count = winter_indices |> Array.filter (fun i -> precip_mm.[i] < 60.0) |> Array.length
                    let summer_dry_count = summer_indices |> Array.filter (fun i -> precip_mm.[i] < 60.0) |> Array.length
                    if winter_dry_count > summer_dry_count then "w"  // winter-dry
                    elif summer_dry_count > winter_dry_count then "s"  // summer-dry
                    else "m"  // monsoon
                else "r"
            let code = sprintf "A%s%s%s" subtype third_letter fourth_letter
            addDetail details "group" (box group)
            addDetail details "subtype" (box subtype)
            code, details

        | "C" -> // Subtropical climates (8+ months ≥10°C)
            // Check for dry seasons
            let summer_dry_months = summer_indices |> Array.filter (fun i -> precip_mm.[i] < 40.0) |> Array.length
            let winter_dry_months = winter_indices |> Array.filter (fun i -> precip_mm.[i] < 40.0) |> Array.length
            
            let subtype = 
                if summer_dry_months >= 3 then "s"  // Mediterranean (dry summer) - at least 3 dry summer months
                elif winter_dry_months >= 3 then "w"  // Winter-dry subtropical (monsoon) - at least 3 dry winter months
                else "f"  // humid subtropical - no distinct dry season
            let code = sprintf "C%s%s%s" subtype third_letter fourth_letter
            addDetail details "group" (box group)
            addDetail details "subtype" (box subtype)
            addDetail details "summer_dry_months" (box summer_dry_months)
            addDetail details "winter_dry_months" (box winter_dry_months)
            code, details

        | "D" -> // Temperate climates (4-7 months ≥10°C)
            let subtype = if coldest >= 0.0 then "o" else "c"  // oceanic vs continental
            
            // Pure Trewartha with UTS: 4-letter codes for both oceanic and continental
            // Do + warmest_thermal + coldest_thermal (e.g., Doak, Dobk)
            // Dc + warmest_thermal + coldest_thermal (e.g., Dcao, Dcbc)
            let code = sprintf "D%s%s%s" subtype third_letter fourth_letter
            
            addDetail details "group" (box group)
            addDetail details "subtype" (box subtype)
            code, details

        | "E" -> // Boreal climates (1-3 months ≥10°C)
            let subtype = if coldest > -10.0 then "o" else "c"  // maritime vs continental subarctic
            let code = sprintf "E%s%s%s" subtype third_letter fourth_letter
            addDetail details "group" (box group)
            addDetail details "subtype" (box subtype)
            code, details

        | "F" -> // Polar climates (0 months ≥10°C)
            let subtype = if warmest > 0.0 then "t" else "i"  // tundra vs ice cap
            let code = sprintf "F%s%s%s" subtype third_letter fourth_letter
            addDetail details "group" (box group)
            addDetail details "subtype" (box subtype)
            code, details

        | _ -> 
            let code = "ERROR"
            addDetail details "error" (box "Unknown climate group")
            code, details


let classify_koppen (temps_c: float[]) (precip_mm: float[]) (latitude: float) : string * Dictionary<string,obj> =
    if temps_c.Length <> 12 || precip_mm.Length <> 12 then raise (ClassificationError "Need 12 monthly temperature and precipitation values")

    let annual_mean_temp = Array.sum temps_c / 12.0
    let annual_precip = Array.sum precip_mm
    let warmest = Array.max temps_c
    let coldest = Array.min temps_c
    let months_ge_10 = temps_c |> Array.filter (fun t -> t >= 10.0) |> Array.length

    let summer_indices, winter_indices =
        if latitude >= 0.0 then ([|3;4;5;6;7;8|], [|9;10;11;0;1;2|]) else ([|9;10;11;0;1;2|],[|3;4;5;6;7;8|])

    let precip_summer = summer_indices |> Array.sumBy (fun i -> precip_mm.[i])
    let precip_winter = winter_indices |> Array.sumBy (fun i -> precip_mm.[i])
    let summer_share = if annual_precip > 0.0 then precip_summer / annual_precip else 0.0
    let winter_share = if annual_precip > 0.0 then precip_winter / annual_precip else 0.0

    let R =
        if summer_share >= 0.70 then 2.0 * annual_mean_temp + 28.0
        elif winter_share >= 0.70 then 2.0 * annual_mean_temp
        else 2.0 * annual_mean_temp + 14.0

    let details = Dictionary<string,obj>()
    addDetail details "annual_mean_temp" (box annual_mean_temp)
    addDetail details "annual_precip" (box annual_precip)
    addDetail details "warmest" (box warmest)
    addDetail details "coldest" (box coldest)
    addDetail details "months_ge_10" (box months_ge_10)
    addDetail details "precip_summer" (box precip_summer)
    addDetail details "precip_winter" (box precip_winter)
    addDetail details "summer_share" (box summer_share)
    addDetail details "winter_share" (box winter_share)
    addDetail details "dryness_threshold_R" (box R)

    let main =
        if annual_precip < R then "B"
        elif Array.forall (fun t -> t >= 18.0) temps_c then "A"
        elif warmest < 10.0 then "E"
        elif coldest > -3.0 then "C"
        else "D"

    if main = "E" then
        let subtype = if warmest > 0.0 then "T" else "F"
        let code = main + subtype
        addDetail details "group" (box main)
        addDetail details "subtype" (box subtype)
        code, details
    elif main = "B" then
        let sub1 = if annual_precip < 0.5 * R then "W" else "S"
        let sub2 = if annual_mean_temp >= 18.0 then "h" else "k"
        let code = sprintf "%s%s%s" main sub1 sub2
        addDetail details "group" (box main)
        addDetail details "sub1" (box sub1)
        addDetail details "sub2" (box sub2)
        code, details
    else
        let summer_months = summer_indices |> Array.map (fun i -> precip_mm.[i])
        let winter_months = winter_indices |> Array.map (fun i -> precip_mm.[i])
        let driest_summer = if Array.isEmpty summer_months then 0.0 else Array.min summer_months
        let driest_winter = if Array.isEmpty winter_months then 0.0 else Array.min winter_months
        let wettest_winter = if Array.isEmpty winter_months then 0.0 else Array.max winter_months
        let wettest_summer = if Array.isEmpty summer_months then 0.0 else Array.max summer_months
        let second =
            if driest_summer < 40.0 && wettest_winter > 0.0 && driest_summer < (wettest_winter / 3.0) then "s"
            elif wettest_summer > 0.0 && driest_winter < (wettest_summer / 10.0) then "w"
            else "f"

        let third =
            if main = "C" || main = "D" then
                if warmest >= 22.0 && months_ge_10 >= 4 then "a"
                elif months_ge_10 >= 4 && warmest < 22.0 then "b"
                elif months_ge_10 >= 1 then "c"
                else "d"
            else ""

        if main = "A" then
            let secondA = if Array.forall (fun p -> p >= 60.0) precip_mm then "f" else (if Array.exists (fun i -> precip_mm.[i] < 60.0) winter_indices && precip_winter < precip_summer then "w" else "m")
            let code = main + secondA
            addDetail details "group" (box main)
            addDetail details "second" (box secondA)
            code, details
        else
            let code = main + second + third
            addDetail details "group" (box main)
            addDetail details "second" (box second)
            addDetail details "third" (box third)
            code, details
