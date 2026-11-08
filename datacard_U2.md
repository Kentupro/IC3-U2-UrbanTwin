# Data card U2 - MOLI-SOL, Node 1 / PM2.5

## 1. Identitate, proveniență și drepturi

Tema: U2 — UrbanTwin — Senzor low-cost vs. stație: calibrare și drift.
Întrebarea: PM2.5 brut și variabilele ambientale pot reduce eroarea față de referință și pot indica necesitatea verificării unui senzor urban?
Client: responsabilul tehnic al rețelei de senzori. Decizie: folosirea datelor sau verificare/recalibrare după diagnostic.

Dataset: Air Quality Data from Regulatory AQMS and Low-Cost Sensors in Molí del Sol, Valencia (May 31 2024 - January 23, 2025). Autori: Guillem Montalbán Faet; Eric Meneses Albalá; Santiago Felici-Castell; Juan José Pérez Solano; Jaume Segura-Garcia. Universitat de València; colector referință: Generalitat Valenciana.
DOI: https://doi.org/10.5281/zenodo.17044034 . Versiune 1.0.0, publicată 03.09.2025. Licență: CC BY 4.0 (confirmată în metadatele API Zenodo la 08.11.2026). Atribuirea și indicarea transformărilor sunt păstrate în README; nu se confundă licența datelor cu cea a codului.
Stație: Molí del Sol, cod 46250048; coordonate 39.48113875, -0.40855865. Node 1 și Node 2: module ZPHS01B co-localizate cu stația. Sursa a fost acceptată în feedbackul CP0.

Arhiva originală: moli-sol-dataset.zip. MD5: 3bda941929caf4090819569399326f16 (egal cu cel publicat). SHA-256: 094f679df8eb75abe567b5374d88a5c3998e83be67c4ba8bfbe26cceef74030a. Inventar complet și hash-uri per CSV în outputs/inventory.csv.

## 2. Perioadă, rezoluție și unitate de observație

Campanie declarată: 31.05.2024–23.01.2025 (238 zile calendaristice). În CSV-urile orare, capete decodate: 31.05.2024 08:00–23.01.2025 09:00 UTC. Grila inclusivă are 5.690 ore; numărul zilelor nu înseamnă 238 × 24 observații efective.
Arhiva conține 9 CSV-uri: GVA, Node 1 și Node 2, fiecare la 10/30/60 minute. Folosim gva_60.csv și n1_60.csv. Celelalte agregări nu sunt exemple independente. Node 2 rămâne rezervă pentru verificare între dispozitive.
Unitate: o pereche orară Node 1–GVA pe același timestamp. rounded_datetime este Unix ns, începutul intervalului. Se decodează UTC; fusul orar local al achiziției nu este explicat suficient în sursă, deci nu se introduce o deplasare suplimentară. Nu folosim variabile de tip ora locală până la clarificare. Aliniere exactă one-to-one, fără nearest-neighbour sau interpolare.

## 3. Dicționarul variabilelor selectate

| Sursă / coloană | Variabilă derivată | Rol | Unitate / tratament |
|---|---|---|---|
| Node 1 / PM2_5 | pm25_raw | Predictor principal; baseline brut | µg/m³; finit, ≥0 |
| GVA / PM2,5 | pm25_reference | Țintă | µg/m³; finit, ≥0; nu se impută |
| Node 1 / Temp | temperature | Predictor auxiliar pentru CP2 | °C; finit; interval observat păstrat |
| Node 1 / HR | rh_raw, rh_qc | Analiză RH separată | %; valid numai în [0,100]; valorile invalide devin NaN doar în rh_qc |
| Ambele / rounded_datetime | timestamp | Cheie temporală | Unix ns → UTC |

GVA HR reproduce PM1; nu este folosită drept umiditate. Temp_Int și HR_Int sunt măsurări interne stației. Vac_Min este integral lipsă. Nu folosim simultan variantele PM2,5 și PM2,5_S/C ca referințe independente. Modelul exact al analizorului PM de referință, etichetele QA ale stației și acoperirea sub-orară a fiecărei medii nu sunt furnizate suficient în arhivă; menținem această limită. Nu presupunem că fiecare medie orară are minimum 75% eșantioane originale.

## 4. Audit și lipsuri măsurate pe arhiva reală

| Indicator | GVA 60 min | Node 1 60 min | Node 2 60 min |
|---|---:|---:|---:|
| Rânduri inițiale | 5.679 | 5.678 | 5.679 |
| Rânduri fără timestamp | 1 | 1 | 1 |
| Timestamp-uri valide, fără duplicate | 5.678 | 5.677 | 5.678 |
| Ore absente din grila de 5.690 | 12 | 13 | 12 |

După eliminarea exclusivă a timestamp-urilor lipsă și join exact: 5.665 ore comune. Dintre acestea, 170 nu au PM2.5 de referință; rămân 5.495 perechi PM valide. În grila completă sunt 195 ore neutilizabile (25 fără pereche de timestamp + 170 fără țintă), adică 3,43%. Nu există timestamp-uri duplicate sau în afara orei exacte în sursele orare verificate.

RH Node 1 >100%: 2.640 din 5.677 rânduri cu timestamp; respectiv 2.572 din 5.495 perechi PM valide (46,81%). RH maxim observat: 118%. Păstrăm măsurarea brută și flag separat; nu plafonăm la 100 și nu inventăm recalibrarea RH. Rămân 2.923 perechi PM cu RH în [0,100]. Acest subset are o distribuție temporală diferită, deci performanța lui nu se compară direct cu cea a tuturor perechilor.

PM2.5 de referință ajunge la 425,3 µg/m³. Nu eliminăm automat vârfurile pe baza erorii față de senzor; nu avem etichete pentru a le declara defecte. Analiza CP2 va raporta separat sensibilitatea la episoade extreme. Arhiva nu conține etichete de drift, mentenanță sau înlocuire a senzorului.

## 5. Împărțire temporală fixată înainte de modelare

| Subset | Interval UTC, capete incluse | Perechi PM | Dintre ele cu RH validă |
|---|---|---:|---:|
| Train | 31.05.2024 08:00–19.10.2024 23:00 | 3.290 | 2.048 |
| Validation | 20.10.2024 00:00–06.12.2024 23:00 | 1.104 | 233 |
| Test | 07.12.2024 00:00–23.01.2025 09:00 | 1.101 | 642 |

Proporții aproximative 60/20/20; limite calendaristice fixe, fără shuffle și fără schimbare după rezultate. Selecția modelului/hiperparametrilor și a pragului folosește train/validation. Testul este rezervat evaluării finale; CP1 îi auditează doar acoperirea/QC. Nicio interpolare a țintei și niciun transformator ajustat pe test. Dacă ulterior se introduc lag-uri, se definește explicit un embargo corespunzător; CP1 nu construiește lag-uri.

## 6. Protocol CP2 și evaluare

Baseline: PM2.5 brut. Modele planificate: regresie liniară și random forest pe PM brut + temperatură, aceiași predictori și aceleași rânduri. RH este investigată separat pe subsetul valid; comparația cu/fără RH se repetă pentru toate modelele pe rânduri identice. Parametrii sunt fixați pe train/validation, seed RF planificat 42. În CP1 ingestia este deterministă, fără seed și fără modele antrenate.
Metrici planificate: MAE, RMSE și bias [µg/m³]; R² predictiv 1−SSE/SST, inclusiv valori negative. Evaluare pe ore valide, raportarea numărului de observații și apoi intervale prin bootstrap pe blocuri temporale în etapa de modelare. Nu se folosește R²=0,98 indoor ca țintă pentru outdoor. Succesul urmărit este reducerea erorii față de PM brut în evaluare temporală, cu incertitudinea și cazurile de eșec raportate; în CP1 nu susținem că reducerea este deja obținută.

## 7. Definiție operațională propusă: «necesită verificare»

Reziduu orar: e(t)=PM_calibrat(t)−PM_referință(t), în µg/m³. Pentru o zi UTC cu minimum 18 perechi orare valide se calculează D(d)=media |e(t)|. După alegerea și înghețarea modelului, pragul q95 este percentila 95 a lui D pe zilele valide din validation. Alertă de verificare dacă D(d)>q95 în 3 zile calendaristice consecutive, fiecare cu minimum 18 perechi; ziua invalidă/lipsă întrerupe secvența. Pragul și regulile se fixează înainte de test.
Este o propunere de protocol pentru următoarea etapă, nu un prag numeric deja estimat. Se urmăresc și biasul semnat și covariatele meteo. Alerta indică o degradare de verificat, nu dovedește drift fizic: aerosolii, sezonalitatea ori referința pot explica reziduul. Fără etichete de drift nu putem raporta sensibilitate/specificitate sau o rată reală a alarmelor false. Necesită referință disponibilă pentru calculul reziduului; în afara co-localizării această regulă nu poate fi aplicată neschimbată.

## 8. Reproductibilitate și limite

Comandă: python src/pipeline.py . Trei verificări automate: carantinarea timestamp-urilor absente, păstrarea PM când RH este invalidă și limitele splitului. Auditul include hash-uri, versiuni Python/pachete și dimensiunile subseturilor. Pipeline-ul rulează pe date reale; modelele și detectorul de drift nu sunt încă implementate la CP1.
Limită majoră: un nod, un sit și mai puțin de un an; nu se separă complet driftul de schimbarea sezonului. Pentru CP4, un caz românesc rămâne opțional și condiționat de o pereche senzor–stație cu proximitate și suprapunere verificabile. Node 2 testează transferul între dispozitive, nu transferul de oraș.
Repo: cod pregătit local pentru IC3-U2-UrbanTwin; URL-ul real se adaugă după publicarea de către autor. Nu există încă un link GitHub verificat în acest livrabil.
