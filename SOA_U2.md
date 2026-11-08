# U2 - State of the art: calibrare și stabilitate în timp

Selecție de 10 articole de cercetare relevante pentru PM2.5, co-localizare, umiditate și transfer temporal. Consultate la 08.11.2026. Rezultatele sunt ale publicațiilor, nu rezultate U2. Metricile, dispozitivele și agregările diferă; tabelul nu este un clasament. R² din regresie/corelație publicată nu este automat identic cu scorul predictiv 1−SSE/SST pe un test temporal.

| ID / articol | Metodă | Date | Metrică | Rezultat | Limită / utilizare în U2 |
|---|---|---|---|---|---|
| 1 / Wang 2019 | Random forest vs. regresie liniară | HK-B3; MicroPEM; expunere controlată indoor | R² | RF: 0,98; liniar: 0,87 | Indoor; performanța nu este țintă pentru Valencia outdoor. |
| 2 / Crilley 2018 | Corecție RH prin teoria κ-Köhler | 14 OPC-N2; urban UK; TEOM-FDMS | Abatere față de referință | După corecție: în limita a 33% | Artefact pozitiv la RH >85%; corecția depinde de aerosol. |
| 3 / Zheng 2018 | Calibrare liniară; efectul mediei temporale | PMS3003; Durham, RTP, Kanpur; E-BAM/FEM | Eroare medie, RTP / T640 | 27% la 1 h; 9% la 24 h | Rezultatele depind de referință, concentrație și agregare. |
| 4 / Badura 2018 | Comparație co-localizată; regresie/CV | 4 modele × 3 unități; Wrocław; TEOM | R² PMS7003; medii 1–60 min | 0,83–0,89 | Supraestimare la RH ridicată; erori mari sub 20–30 µg/m³. |
| 5 / Bulot 2019 | Comparație de lungă durată | Senzori optici; Southampton; stație de fond apropiată | Pearson r (nu R²) | 0,61 < r < 0,88 | Compoziția și nivelul PM schimbă răspunsul; proximitatea nu elimină diferențele spațiale. |
| 6 / Crilley 2020 | Corecție κ-Köhler; higroscopicitate locală | OPC-N2; 4 orașe / 3 continente; referințe co-localizate | Abatere PM2.5 corectat | În limita a 33% la toate siturile | La RH >60% contează compoziția; κ local este preferabil. |
| 7 / Hagan & Kroll 2020 | Simulare fizică Mie; opcsim | Populații de aerosoli simulate; OPC/nefelometre | Eroare fracțională de masă | Depinde de RH, proprietăți optice și mărime | Rezultat mecanistic; nu raportează un singur scor outdoor transferabil. |
| 8 / Holder 2020 | Corecție specifică senzorului pentru fum | Senzori low-cost; PM2.5 orar; incendii outdoor | MAE [µg/m³] | <10 după corecția specifică fumului | Regim de fum; nu este prag general pentru poluarea urbană. |
| 9 / Barkjohn 2021 | Regresie liniară cu termen RH | PurpleAir; ~12.000 medii zilnice; 16 state SUA; FRM/FEM | RMSE [µg/m³]; medii 24 h | 8 → 3 | Agregare zilnică și alt dispozitiv; nu comparăm direct cu RMSE orar U2. |
| 10 / Campmier 2023 | Regresii optimizate; calibrare sezonieră | PA-II; Delhi, Hamirpur, Bengaluru; BAM | NRMSE; R², validare încrucișată | 20–30%; 0,82–0,95 | Calibrările scurte nu se transferă sigur între sezoane; justifică split temporal. |

## Bibliografie

[1] Wang, Y.; Du, Y.; Wang, J.; Li, T. Calibration of a low-cost PM2.5 monitor using a random forest model. Environment International 133, 105161 (2019). https://doi.org/10.1016/j.envint.2019.105161

[2] Crilley, L. R. et al. Evaluation of a low-cost optical particle counter (Alphasense OPC-N2) for ambient air monitoring. Atmospheric Measurement Techniques 11, 709–720 (2018). https://doi.org/10.5194/amt-11-709-2018

[3] Zheng, T. et al. Field evaluation of low-cost particulate matter sensors in high- and low-concentration environments. Atmospheric Measurement Techniques 11, 4823–4846 (2018). https://doi.org/10.5194/amt-11-4823-2018

[4] Badura, M.; Batog, P.; Drzeniecka-Osiadacz, A.; Modzel, P. Evaluation of Low-Cost Sensors for Ambient PM2.5 Monitoring. Journal of Sensors 2018, Article 5096540 (2018). https://doi.org/10.1155/2018/5096540

[5] Bulot, F. M. J. et al. Long-term field comparison of multiple low-cost particulate matter sensors in an outdoor urban environment. Scientific Reports 9, Article 7497 (2019). https://doi.org/10.1038/s41598-019-43716-3

[6] Crilley, L. R. et al. Effect of aerosol composition on the performance of low-cost optical particle counter correction factors. Atmospheric Measurement Techniques 13, 1181–1193 (2020). https://doi.org/10.5194/amt-13-1181-2020

[7] Hagan, D. H.; Kroll, J. H. Assessing the accuracy of low-cost optical particle sensors using a physics-based approach. Atmospheric Measurement Techniques 13, 6343–6355 (2020). https://doi.org/10.5194/amt-13-6343-2020

[8] Holder, A. L. et al. Field Evaluation of Low-Cost Particulate Matter Sensors for Measuring Wildfire Smoke. Sensors 20(17), 4796 (2020). https://doi.org/10.3390/s20174796

[9] Barkjohn, K. K.; Gantt, B.; Clements, A. L. Development and application of a United States-wide correction for PM2.5 data collected with the PurpleAir sensor. Atmospheric Measurement Techniques 14, 4617–4637 (2021). https://doi.org/10.5194/amt-14-4617-2021

[10] Campmier, M. J. et al. Seasonally optimized calibrations improve low-cost sensor performance: long-term field evaluation of PurpleAir sensors in urban and rural India. Atmospheric Measurement Techniques 16, 4357–4374 (2023). https://doi.org/10.5194/amt-16-4357-2023

## Poziționarea experimentului U2

Comparație pe un nod ZPHS01B și o locație outdoor: PM brut → regresie liniară → RF, pe aceleași rânduri și aceiași predictori pentru modelele calibrate. Evaluare cronologică și analiză separată a umidității invalide. Contribuția urmărită este un protocol verificabil de calibrare și alertare persistentă, nu depășirea unui scor indoor. Limite: lipsa etichetelor de drift, sezonalitate, o campanie sub un an. Articolele de mai sus studiază în mare parte alte dispozitive; rezultatele lor motivează protocolul, fără a valida automat ZPHS01B.
