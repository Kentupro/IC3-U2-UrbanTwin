# CP2 — Reprezentare: baseline și protocol

**U2 — UrbanTwin — Senzor low-cost vs. stație: calibrare și drift**

## Întrebarea și progresul față de CP1

Întrebarea rămâne calibrarea PM2.5 față de referință și identificarea necesității verificării senzorului. Clientul este responsabilul tehnic al rețelei. În CP1 am auditat datele. În CP2 am construit reprezentările, am antrenat și evaluat baseline-urile și am fixat protocolul de comparație temporală. Rezultatele de mai jos provin din rulări pe arhiva reală MOLI-SOL, nu din articole sau date sintetice.

## Reprezentarea aleasă și alternativa

Unitate de observație: o oră, cu senzori co-localizați. R0(t)=[PM2.5_brut(t)], în µg/m³. R1(t)=[PM2.5_brut(t), T_nod(t)], cu T în °C. Ținta este PM2.5_GVA(t), la același timestamp. R1 reprezintă candidatul principal cu temperatură; R0 este alternativa mai simplă. Se folosesc 3.290 observații train și 1.104 validation, identice pentru ambele reprezentări și toate metodele. Nu se adaugă informație de la referință în predictori.

Fără scalare, PCA sau lag-uri în CP2. RF împarte variabilele prin praguri, iar regresia liniară are intercept; scalarea nu este necesară aici. Evaluăm calibrarea contemporană, nu prognoza cu o oră înainte. De aceea, comparatorul fără calibrare este PM brut la ora t. Nu folosim PM de referință la t−1 drept persistență, deoarece ar presupune o măsurare de referință în exploatare.

RH este exclusă din reprezentările CP2: 2.572 din 5.495 perechi valide au RH >100% (46,8%). GVA HR reproduce PM1 și nu poate înlocui umiditatea. Nu plafonăm valorile și nu eliminăm aceste ore din analiza principală. Subsetul cu RH validă are doar 233 observații în validation; un experiment viitor cu RH trebuie să compare toate modelele pe același subset și să raporteze selecția sezonieră.

## Protocol experimental

| Subset | Interval UTC, capete incluse | Perechi valide |
|---|---|---:|
| Train | 31.05.2024 08:00–19.10.2024 23:00 | 3.290 |
| Validation | 20.10.2024 00:00–06.12.2024 23:00 | 1.104 |
| Test rezervat | 07.12.2024 00:00–23.01.2025 09:00 | 1.101 |

Păstrăm limitele fixate la CP1, înaintea modelării. Splitul temporal simulează folosirea calibrării după perioada de antrenare și evită amestecarea unor ore vecine între subseturi. Nu folosim shuffle, interpolarea țintei sau lag-uri care ar traversa splitul. Datele de test sunt auditate la ingestie, dar sunt eliminate înainte de construirea matricelor pentru modelare. Nu calculăm metrici ori alerte pe test la CP2.

Baseline-uri executate:

1. Senzor brut: predicție egală cu PM brut, fără ajustare.
2. Media referinței din train: comparator constant, fără acces la validation pentru estimarea mediei. Este un baseline de tip climatologie globală pe perioada train, nu o climatologie multianuală.
3. Regresie liniară cu intercept, pe R0 și R1, ajustată numai pe train.
4. Random Forest pe R0 și R1, aceleași setări: 300 arbori, max_depth=8, min_samples_leaf=5, max_features=1.0, bootstrap=True, n_jobs=1. Seed-uri: 42, 7, 21, 84, 123. Nu s-a executat căutare de hiperparametri.

În total: 12 ajustări de modele (2 liniare și 10 RF). Cele două baseline-uri fără ajustare sunt calculate separat. Nu plafonăm predicțiile și nu eliminăm valori extreme pe baza erorii. Reprezentarea RF se selectează după MAE mediu pe cele 5 seed-uri de validation; la egalitate se preferă R0. Selecția rămâne provizorie până la evaluarea pe date noi.

Metrici: MAE=media |ŷ−y|, RMSE=radical(media (ŷ−y)²), bias=media (ŷ−y), toate în µg/m³. R²=1−SSE/SST este scor predictiv pe validation și poate fi negativ; nu îl înlocuim cu pătratul corelației Pearson. MAE este criteriul principal, dar RMSE și biasul sunt raportate pentru a expune erorile mari și supra/subestimarea.

## Rezultate pe validation

Toate rândurile din tabel folosesc aceleași 1.104 ore. Pentru RF, valorile sunt media metricilor individuale ± deviația standard între 5 seed-uri. Aceasta nu este un interval de încredere și nu este scorul unui ensemble al predicțiilor.

| Model | MAE [µg/m³] | RMSE [µg/m³] | Bias [µg/m³] | R² predictiv |
|---|---:|---:|---:|---:|
| Senzor brut | 11.181 | 12.084 | 10.431 | -0.270 |
| Media referinței din train | 6.967 | 10.928 | -2.116 | -0.039 |
| Regresie liniară / R0 | 4.365 | 6.422 | 0.488 | 0.641 |
| Regresie liniară / R1 | 4.435 | 6.429 | 0.642 | 0.640 |
| Random Forest / R0 | 4.798 ± 0.016 | 7.483 ± 0.053 | 0.555 ± 0.025 | 0.513 ± 0.007 |
| Random Forest / R1 | 4.317 ± 0.019 | 7.776 ± 0.062 | -0.918 ± 0.045 | 0.474 ± 0.008 |


R1 este selectată pentru RF după MAE: **4.317 µg/m³**, cu **61.39%** sub senzorul brut. În comparația controlată RF, adăugarea temperaturii reduce MAE cu **10.03%**, dar crește RMSE cu **3.91%**. R² scade. Nu putem afirma că R1 domină pe toate criteriile.

Regresia liniară R0 obține RMSE **6.422 µg/m³**, mai bun decât RF/R1. Diferența MAE RF/R1 față de liniar/R0 este mică (aproximativ 0.048 µg/m³); nu demonstrăm superioritatea RF față de regresie prin această comparație. Liniar/R0 rămâne comparator obligatoriu la CP3.

Verificare exploratorie a sensibilității: bootstrap pereche pe cele 48 zile UTC de validation, 2.000 resamplări, seed=2026. Se compară eroarea absolută medie peste seed-uri, pe exact aceleași ore. ΔMAE(R1−R0)=-0.481 µg/m³, interval percentilă 95% **[-0.873, -0.080]**. Intervalul este condiționat de modelele deja ajustate și de această fereastră de validation. Nu include incertitudinea antrenării sau a selecției modelului și nici autocorelația dintre zile; nu înlocuiește testul temporal rezervat.

Exemplu de eșec păstrat în evaluare: la 28.11.2024 09:00 UTC, referința are 99,8 µg/m³, iar RF/R1, seed 42, estimează aproximativ 11,05 µg/m³. MAE mediu mai mic nu garantează detectarea vârfurilor. Un singur nod, o singură locație și o campanie sub un an nu demonstrează transferul între orașe sau separarea driftului de sezonalitate.

## «Necesită verificare»: răspuns la feedback

Păstrăm precizarea profesoarei: R²=0,98 din Wang este indoor și nu constituie țintă pentru Valencia outdoor. Nu interpretăm valoarea mai mică obținută aici ca eșec față de un obiectiv impus.

Protocol propus pentru următoarea etapă: reziduu e(t)=PM_calibrat(t)−PM_referință(t). Pentru fiecare zi UTC cu minimum 18 perechi valide, D(d)=media |e(t)|. Pragul q95 se estimează din zilele eligibile de validation, după fixarea modelului. Se solicită verificare când D(d)>q95 în 3 zile calendaristice consecutive; o zi lipsă sau insuficient acoperită întrerupe seria. Modelul și pragul trebuie înghețate înainte de test.

Ca verificare de fezabilitate, pentru baseline-ul RF/R1, seed 42, q95 este **17.627 µg/m³**, estimat din **46 zile** cu minimum 18 perechi. Este un prag exploratoriu specific acestui model, nu un prag fizic universal. În CP2 nu validăm detectorul, nu calculăm alarme pe test și nu raportăm o rată reală a alarmelor false. Dacă modelul se schimbă la CP3, pragul trebuie recalibrat pe date de dezvoltare, înaintea oricărei evaluări finale.

Alerta necesită referință co-localizată pentru calculul reziduului și cere diagnostic. Poate reflecta meteorologia, aerosolii sau o problemă a referinței, nu numai drift fizic. Sugestia pentru CP4 rămâne transferul opțional într-un oraș românesc, numai dacă este găsită o pereche senzor–stație cu proximitate și suprapunere temporală verificate. Node 2 ar testa transferul între dispozitive, nu transferul de oraș.

## Reproducere și fișiere

Rulare din rădăcina repo-ului: `python download_data.py`, `python cp2.py`, `python -m unittest discover -v`. Pentru instalarea mediului, vezi README. Arhiva este verificată înainte de procesare. Versiuni utilizate: Python 3.12.14, NumPy 2.3.5, pandas 2.2.3, scikit-learn 1.8.0.

- `results/cp2/metrics.csv`: tabelul agregat de validation.
- `results/cp2/metrics_by_seed.csv`: rezultatele individuale.
- `results/cp2/validation_predictions.csv`: predicții pentru verificare, seed 42 la RF.
- `results/cp2/manifest.json`: setări, seed-uri, hash-uri, limite temporale, selecție și confirmarea `test_scored=false`.
- `test_cp2.py`: verifică metricile, splitul și faptul că datele viitoare de test nu pot schimba rezultatele de validation.

Sursa datelor și cele zece articole rămân documentate în datacard_U2.md și SOA_U2.md. Documentație metodologică: https://scikit-learn.org/1.8/modules/generated/sklearn.ensemble.RandomForestRegressor.html și https://scikit-learn.org/1.8/modules/generated/sklearn.metrics.r2_score.html .
