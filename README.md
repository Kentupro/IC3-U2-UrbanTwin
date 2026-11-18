# U2 — UrbanTwin — Senzor low-cost vs. stație: calibrare și drift

Proiect IC3. Calibrare PM2.5 pentru Node 1, co-localizat cu stația Molí del Sol din Valencia. CP1 documentează datele și controlul calității. CP2 compară două reprezentări orare și baseline-uri, pe un split temporal fix.

## Rulare

Python 3.12, din rădăcina repo-ului. Pe Windows, în terminalul VS Code:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe download_data.py
.\.venv\Scripts\python.exe cp2.py
.\.venv\Scripts\python.exe -m unittest discover -v
```

Linux/macOS: creează mediul cu `python3 -m venv .venv` și folosește `.venv/bin/python` în locul interpretorului Windows. Arhiva poate fi și copiată manual la `data/raw/moli-sol-dataset.zip`. Descărcarea verifică checksum-ul publicat. Datele brute și intermediarii din `outputs/` sunt excluși din Git.

`python pipeline.py` rulează doar ingestia CP1. `python cp2.py` reface ingestia și întregul experiment CP2, inclusiv metricile și predicțiile de validation.

## Protocol și rezultate CP2

- R0: PM2.5 brut; R1: PM2.5 brut + temperatura nodului. Țintă: PM2.5 GVA, aceeași oră.
- Train: înainte de 20.10.2024, 3.290 perechi. Validation: 20.10–06.12.2024, 1.104 perechi. Test: de la 07.12.2024, 1.101 perechi rezervate. Limite la 00:00 UTC.
- Baseline-uri: senzor brut, media referinței din train, regresie liniară și Random Forest. RF folosește 300 arbori, adâncime 8 și minimum 5 exemple în frunză, cu 5 seed-uri fixe. Fără căutare de hiperparametri.
- Pe validation, RF/R1 obține MAE mediu **4,317 µg/m³**, față de **11,181** pentru senzorul brut. RF/R0: **4,798**. Temperatura reduce MAE pentru RF, dar crește RMSE de la **7,483** la **7,776**. Regresia liniară R0 are RMSE **6,422**.
- Alegem provizoriu R1 pentru RF după MAE pe validation. Regresia liniară R0 rămâne comparator obligatoriu la CP3. Testul nu este evaluat și nu intră în selecție.

Protocolul, limitele și interpretarea sunt în [CP2_U2.md](CP2_U2.md). Tabelul complet este în [results/cp2/metrics.csv](results/cp2/metrics.csv). [manifest.json](results/cp2/manifest.json) înregistrează configurația, seed-urile, versiunile și hash-urile. [metrics_by_seed.csv](results/cp2/metrics_by_seed.csv) păstrează rulările individuale. [validation_predictions.csv](results/cp2/validation_predictions.csv) conține predicțiile seed-ului 42 pentru verificare.

## Calitatea datelor

5.495 perechi PM valide din 5.690 ore posibile. În 46,8% dintre perechi, nodul raportează RH >100%. Păstrăm valorile brute și marcajele QC; RH nu intră în modelele CP2. GVA `HR` reproduce PM1 și este exclusă. Nu imputăm ținta și nu eliminăm vârfurile de PM doar pentru că sunt greu de prezis.

[Data card](datacard_U2.md) · [State of the art: 10 articole](SOA_U2.md) · [Audit CP1](audit.json).

## Date și licențe

Montalbán Faet, G.; Meneses Albalá, E.; Felici-Castell, S.; Pérez Solano, J. J.; Segura-Garcia, J. (2025). *Air Quality Data from Regulatory AQMS and Low-Cost Sensors in Molí del Sol, Valencia*, v1.0.0. DOI: [10.5281/zenodo.17044034](https://doi.org/10.5281/zenodo.17044034). Date: **CC BY 4.0**. CSV-urile derivate aliniază timestamp-uri, redenumesc coloane și adaugă marcaje QC și predicții. Cod: **MIT**, conform [LICENSE](LICENSE).
