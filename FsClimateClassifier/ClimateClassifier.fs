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
    let summer_share = if annual_precip > 0.0 then precip_summer / annual_precip else 0.0
    let winter_share = if annual_precip > 0.0 then precip_winter / annual_precip else 0.0

    let R =
        if summer_share >= 0.70 then 2.0*annual_mean_temp + 28.0
        elif winter_share >= 0.70 then 2.0*annual_mean_temp
        else 2.0*annual_mean_temp + 14.0

    let details = Dictionary<string,obj>()
    addDetail details "annual_mean_temp" (box annual_mean_temp)
    addDetail details "annual_precip" (box annual_precip)
    addDetail details "warmest" (box warmest)
    addDetail details "coldest" (box coldest)
    addDetail details "months_ge_10" (box m10)
    addDetail details "precip_summer" (box precip_summer)
    addDetail details "precip_winter" (box precip_winter)
    addDetail details "summer_share" (box summer_share)
    addDetail details "winter_share" (box winter_share)
    addDetail details "dryness_threshold_R" (box R)

    if annual_precip < R then
        let sub1 = if annual_precip < 0.5 * R then "W" else "S"
        let temp_qual = if annual_mean_temp >= 18.0 then "h" else "k"
        let code = sprintf "B%s%s" sub1 temp_qual
        addDetail details "group" (box "B")
        addDetail details "sub1" (box sub1)
        addDetail details "temp_qual" (box temp_qual)
        addDetail details "four_letter" (box false)
        code, details
    else
        let group =
            if Array.forall (fun t -> t >= 18.0) temps_c then "A"
            elif m10 >= 8 then "C"
            elif m10 >= 4 && m10 <= 7 then "D"
            elif m10 >= 1 && m10 <= 3 then "E"
            else "F"

        let thermal_letter mean_t =
            if mean_t >= 35.0 then "i"
            elif mean_t >= 28.0 then "h"
            elif mean_t >= 22.2 then "a"
            elif mean_t >= 18.0 then "b"
            elif mean_t >= 10.0 then "l"
            elif mean_t >= 0.1 then "k"
            elif mean_t >= -9.9 then "o"
            elif mean_t >= -24.9 then "c"
            elif mean_t >= -39.9 then "d"
            else "e"

        if group = "F" then
            let subtype = if warmest >= 0.0 && warmest < 10.0 then "T" elif warmest < 0.0 then "F" else "T"
            let second = "f"
            let summer_letter = "c"
            let t_letter = thermal_letter annual_mean_temp
            let code = sprintf "%s%s%s%s" group second summer_letter t_letter
            addDetail details "group" (box group)
            addDetail details "subtype" (box subtype)
            addDetail details "second" (box second)
            addDetail details "third" (box summer_letter)
            addDetail details "thermal_scale" (box t_letter)
            addDetail details "four_letter" (box true)
            code, details
        else
            // seasonality letters
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
                if List.contains group ["C";"D";"E";"A"] then
                    if warmest >= 22.0 then "a"
                    elif m10 >= 4 then "b"
                    else "c"
                else ""

            let t_letter = thermal_letter annual_mean_temp
            let code = if third <> "" then sprintf "%s%s%s%s" group second third t_letter else sprintf "%s%s%s" group second t_letter
            addDetail details "four_letter" (box (third <> ""))
            addDetail details "thermal_scale" (box t_letter)
            addDetail details "group" (box group)
            addDetail details "second" (box second)
            addDetail details "third" (box third)
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
