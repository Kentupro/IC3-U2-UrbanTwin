# CP3 — Învățare: rezultate v1

**U2 — UrbanTwin — Senzor low-cost vs. stație: calibrare și drift**

## Ce am executat

Am evaluat configurațiile fixate la CP2 pe cele 1.101 perechi orare din testul rezervat: 07.12.2024 00:00–23.01.2025 09:00 UTC. Am refăcut cele 12 ajustări numai pe train (3.290 ore), am verificat reproducerea MAE de validation din CP2 pentru toate cele șase metode și am calculat scorurile pe test abia după aceste verificări. Nu am reantrenat pe validation, nu am căutat hiperparametri și nu am ales alt model după consultarea testului.

Protocolul și codul de evaluare au fost publicate înaintea calculării scorurilor, în [commitul 315c206](https://github.com/Kentupro/IC3-U2-UrbanTwin/commit/315c206ebc735ccc137750a6696f6c4ba5a3298a). Baza CP2 este commitul 721152704cf033d237cda2ea9743bb2e86bf98ac. Fișierul `protocol_cp3.json` păstrează setările, hash-urile sursei și regula de monitorizare. Acest pas fixează experimentul CP3; nu este o înregistrare externă a studiului.

## Metoda și baseline-urile

Metoda principală rămâne RF/R1, selectată la CP2 după MAE de validation. R0=[PM2.5 brut], iar R1=[PM2.5 brut, temperatura nodului]. Ținta este PM2.5 de referință, la aceeași oră. Toate metodele folosesc exact aceleași ore de test, cu unități µg/m³ pentru PM și °C pentru temperatură.

Comparăm senzorul brut, media referinței din train, regresia liniară cu intercept pe R0/R1 și RF pe R0/R1. RF păstrează 300 arbori, max_depth=8, min_samples_leaf=5, max_features=1.0, bootstrap=True, n_jobs=1. Seed-uri: 42, 7, 21, 84, 123. Nu folosim umiditatea invalidă, referința drept predictor, lag-uri, interpolarea țintei, plafonarea predicțiilor sau eliminarea valorilor extreme pe baza erorii.

Rezultatele sunt pentru calibrare contemporană, nu prognoză. Transferul între orașe nu este evaluat aici.

## Rezultate reale pe test

| Metodă | MAE [IC 95%], µg/m³ | RMSE [IC 95%], µg/m³ | Bias, µg/m³ | R² |
|---|---:|---:|---:|---:|
| Senzor brut | 12.696 [11.140; 14.451] | 17.772 [12.080; 25.306] | 11.216 | -0.318 |
| Media train | 6.142 [5.002; 7.897] | 15.484 [6.124; 25.669] | 0.351 | -0.001 |
| Liniar / R0 | 4.814 [3.698; 6.528] | 13.850 [4.765; 23.433] | 1.461 | 0.199 |
| Liniar / R1 | 4.985 [3.876; 6.711] | 13.887 [4.897; 23.440] | 1.727 | 0.195 |
| RF / R0 | 4.706 [3.383; 6.604] | 14.338 [4.953; 24.198] | 1.075 | 0.142 |
| RF / R1 | 3.839 [2.504; 5.861] | 14.320 [4.010; 24.500] | -0.994 | 0.144 |


RF/R1 obține MAE **3.839 µg/m³**, față de **12.696** pentru senzorul brut: reducere de **69.76%** pe această fereastră de test. Față de liniar/R0, diferența MAE este de aproximativ **-0.975 µg/m³**.

Pentru RF, tabelul folosește **media metricilor individuale din cele 5 seed-uri**, nu predicția unui ensemble. Deviația standard între seed-uri a MAE RF/R1 este **0.0129 µg/m³**. Ea exprimă variația algoritmică și nu trebuie confundată cu intervalul de încredere temporal. Fișierul `results_v1_U2.csv` conține 6 rânduri agregate și 10 rânduri individuale pentru seed-urile RF; include intervale pentru MAE, RMSE, bias și R².

## Cum calculăm intervalele de încredere

Folosim bootstrap cu blocuri mobile, necircular, de **3 zile calendaristice UTC consecutive**, 3.000 resamplări, seed=20261122, intervale percentile 95%. Calendarul complet al testului are 48 zile; datele fără observații rămân în calendar. Fiecare replică extrage blocuri cu înlocuire și păstrează toate perechile orare valide ale zilelor extrase. Nu tratăm cele 1.101 ore ca observații independente.

Aceleași extrageri se aplică tuturor metodelor, deci diferențele sunt **pereche**. Pentru RF calculăm metrica fiecărui seed în replică și apoi media celor 5 metrici. Modelele nu sunt reajustate în bootstrap. Intervalele sunt condiționate de train-ul fix și de această fereastră de test; nu cuprind incertitudinea selecției modelului sau a altor perioade de antrenare. Blocurile reduc problema dependenței temporale locale, dar nu garantează acoperirea nominală dacă dependența persistă mult peste 3 zile.

Nu folosim îngustimea intervalului între seed-uri pentru a afirma generalizarea temporală. Lățimea intervalelor RMSE reflectă și sensibilitatea la episoade rare cu concentrații mari.

## Metoda față de baseline: diferențe pereche

Diferență = RF/R1 minus baseline. Pentru MAE și RMSE, o valoare negativă favorizează RF/R1.

| Contrast | Metrică | Diferență | IC 95% |
|---|---|---:|---|
| RF/R1 − Senzor brut | MAE | -8.857 | [-10.554; -6.804] |
| RF/R1 − Senzor brut | RMSE | -3.452 | [-9.413; -0.568] |
| RF/R1 − Liniar / R0 | MAE | -0.975 | [-1.564; -0.325] |
| RF/R1 − Liniar / R0 | RMSE | 0.470 | [-0.946; 1.153] |
| RF/R1 − RF / R0 | MAE | -0.867 | [-1.524; -0.230] |
| RF/R1 − RF / R0 | RMSE | -0.018 | [-1.311; 0.378] |


Intervalele diferențelor MAE față de senzorul brut, liniar/R0 și RF/R0 sunt sub zero în acest experiment. Pentru RMSE față de liniar/R0, intervalul cuprinde zero. Prin urmare, **nu demonstrăm un avantaj RF/R1 pe RMSE față de modelul liniar**. Nu deducem superioritatea din simpla suprapunere sau nesuprapunere a intervalelor individuale.

## Rezultatul negativ și cazurile de eșec

RMSE RF/R1 este **14,320 µg/m³**, față de **13,850 µg/m³** pentru liniar/R0. R² RF/R1 este doar **0,144**, chiar dacă MAE mediu scade. Aceste rezultate rămân în raport și în prezentare.

La **26.12.2024 00:00 UTC**, referința are **425,30 µg/m³**, senzorul brut **53,97 µg/m³**, RF/R1 cu seed 42 estimează **20,34 µg/m³**, iar liniar/R0 aproximativ **40,41 µg/m³**. Toate subestimează această oră. Numai acest punct contribuie cu aproximativ **72,64%** la suma erorilor pătratice a RF/R1, seed 42. Nu îl eliminăm pentru a îmbunătăți scorul și nu atribuim automat episodul unei cauze fizice fără verificare independentă.

Concluzia susținută este că RF/R1 îmbunătățește eroarea absolută medie pe testul ales, dar **nu măsoară fiabil toate vârfurile**. Metoda nu poate fi declarată înlocuitor al stației de referință. Un singur nod, un sit și mai puțin de un an limitează generalizarea. Nu confundăm schimbarea distribuției sezoniere cu driftul fizic.

## Verificarea persistentă a senzorului

Am implementat și aplicat regula propusă după feedbackul CP0. Pentru RF/R1, seed 42, păstrăm pragul din CP2: **q95=17,627154 µg/m³**, estimat pe 46 zile eligibile de validation. O zi este eligibilă dacă are minimum 18 perechi valide. Semnalăm verificare la a treia zi calendaristică consecutivă cu MAE zilnic strict peste prag; o zi lipsă sau insuficient acoperită întrerupe seria. Pragul nu se ajustează pe test.

Pe test avem **45 zile eligibile**, **1 zi peste prag** și **0 zile cu alertă persistentă**. Acesta este un rezultat al regulii fixate, nu dovada că senzorul nu are drift și nici o rată măsurată de alarme false. Nu există etichete de drift/defect în date. Regula necesită referința co-localizată pentru calculul reziduurilor. Faptul că vârfurile orare pot fi ratate arată și limita unei reguli bazate pe media zilnică și pe persistență de 3 zile.

Păstrăm precizarea profesoarei: R²=0,98 din Wang privește indoor și nu constituie țintă pentru Valencia outdoor. Un caz nou din România rămâne posibil la CP4 numai dacă există proximitate și suprapunere temporală verificate pentru perechea senzor–stație. Node 2 poate evalua transferul între dispozitive, nu transferul de oraș.

## Reproducere și fișiere

Din rădăcina repo-ului, după instalarea dependențelor din README:

```powershell
python download_data.py
python cp3.py
python -m unittest discover -v
```

- `results_v1_U2.csv`: fișierul cerut la CP3, agregate și seed-uri cu IC 95%.
- `results/cp3/paired_differences.csv`: diferențe pereche față de baseline-uri.
- `results/cp3/test_predictions.csv`: predicțiile tuturor seed-urilor, cu timestamp și referință.
- `results/cp3/daily_monitoring.csv`: acoperire zilnică, depășiri și alerte.
- `results/cp3/manifest.json`: hash-uri, versiuni și verificări ale protocolului.

Cele **14 teste automate** includ comparația bootstrap-ului cu resamplarea explicită a orelor, păstrarea blocurilor consecutive, predicția fără coloana țintă din test și resetarea secvenței de alertă la goluri. Datele brute rămân excluse din Git. Sursă: MOLI-SOL v1.0.0, DOI https://doi.org/10.5281/zenodo.17044034 , CC BY 4.0. Codul păstrează licența MIT a repo-ului.

Testul a fost acum evaluat. Orice dezvoltare ulterioară trebuie să declare folosirea acestuia și să obțină date independente pentru o nouă evaluare finală; nu reglăm modelul pe acest test și apoi nu îl prezentăm din nou drept nevăzut.
