# Pharmora

Pharmora est un assistant d’information pharmaceutique basé sur une architecture RAG, conçu pour fournir des réponses claires et sourcées à partir de documents pharmaceutiques officiels.

L’application permet d’identifier un médicament par recherche textuelle ou à partir d’une photo de sa boîte, puis de poser des questions contextualisées sur ce médicament.

Application déployée : https://pharmora.streamlit.app/

## Fonctionnalités principales

- Recherche de médicaments par nom, dosage et forme pharmaceutique
- Identification d’un médicament à partir d’une photo de boîte
- Extraction OCR locale avec RapidOCR
- Exécution OCR avec ONNX Runtime
- Identification contrôlée à partir d’un catalogue pharmaceutique
- Fiche structurée du médicament sélectionné
- Questions/réponses basées sur les RCP et documents pharmaceutiques
- Retrieval sémantique avec embeddings multilingues et FAISS
- Réécriture automatique des requêtes lorsque nécessaire
- Gestion du contexte conversationnel
- Réponses accompagnées des sources pharmaceutiques utilisées
- Gestion des cas ambigus ou non reconnus
- Garde-fous pour éviter les décisions médicales personnalisées

## Principe de fonctionnement

Pharmora sépare l’identification du médicament, la recherche documentaire et la génération de réponse.

```text
Identification du médicament
        ↓
Catalogue pharmaceutique
        ↓
Médicament actif
        ↓
Conversation contextualisée
        ↓
Retrieval documentaire
        ↓
Sélection des passages pertinents
        ↓
Génération de la réponse
        ↓
Validation
        ↓
Réponse + sources
```

Pour l’identification à partir d’une image :

```text
Photo de la boîte
        ↓
RapidOCR
        ↓
Extraction du texte
        ↓
Nom + dosage + forme
        ↓
Catalogue
        ↓
Identification du médicament
```

L’OCR ne décide pas directement de l’identité du médicament.

Le texte extrait est utilisé pour rechercher une spécialité dans un catalogue pharmaceutique contrôlé.

Cette séparation permet d’éviter qu’une erreur OCR entraîne automatiquement une identification arbitraire.

## Architecture RAG

Le corpus documentaire est préparé avant l’exécution de l’application.

### Pipeline offline

```text
Sources pharmaceutiques
        ↓
Acquisition des documents
        ↓
Extraction
        ↓
Nettoyage et normalisation
        ↓
Structuration
        ↓
Chunking
        ↓
Embeddings
        ↓
Index FAISS
```

Les documents pharmaceutiques sont structurés par sections avant le chunking afin de préserver leur contexte documentaire.

### Pipeline online

```text
Question utilisateur
        ↓
Contextualisation
        ↓
Retrieval
        ↓
Sélection des passages pertinents
        ↓
Réécriture éventuelle de la requête
        ↓
Génération de la réponse
        ↓
Validation des références
        ↓
Réponse + sources
```

Le retrieval repose sur des embeddings multilingues générés avec :

```text
intfloat/multilingual-e5-small
```

Les vecteurs sont indexés avec FAISS afin de retrouver les passages les plus pertinents pour chaque question.

## Gestion conversationnelle

Pharmora conserve le contexte de la conversation lié au médicament sélectionné.

Cela permet de gérer des questions de suivi telles que :

```text
Quels sont ses effets indésirables ?
```

puis :

```text
Et pendant la grossesse ?
```

La deuxième question est contextualisée avant d’être envoyée au pipeline RAG.

Un changement de médicament crée un nouveau contexte conversationnel.

## Sources pharmaceutiques

Le corpus de Pharmora est construit à partir de la Base de données publique des médicaments.

Les documents utilisés comprennent notamment :

- les Résumés des Caractéristiques du Produit
- les notices pharmaceutiques
- les informations structurées des médicaments

Les réponses sont générées à partir des passages sélectionnés dans ces documents.

Les sources utilisées sont affichées séparément dans l’interface afin de permettre leur consultation.

## Médicaments disponibles dans la V1

La V1 utilise actuellement un catalogue volontairement limité à 15 spécialités pharmaceutiques.

### Doliprane

- DOLIPRANE 500 mg, gélule
- DOLIPRANE 1000 mg, gélule
- DOLIPRANE 500 mg, comprimé

### Amoxicilline

- AMOXICILLINE BENTA 500 mg, gélule
- AMOXICILLINE SANDOZ 500 mg, gélule
- AMOXICILLINE EG LABO 500 mg, gélule

### Ibuprofène

- IBUPROFENE ARROW 5 %, gel
- IBUPROFENE EG 200 mg, comprimé pelliculé
- IBUPROFENE EG 400 mg, comprimé pelliculé

### Cétirizine

- CETIRIZINE EG 10 mg, comprimé pelliculé sécable
- CETIRIZINE ALMUS 10 mg, comprimé pelliculé sécable
- CETIRIZINE EG LABO CONSEIL 10 mg, comprimé à sucer

### Oméprazole

- OMEPRAZOLE ZENTIVA CONSEIL 20 mg, gélule
- OMEPRAZOLE EG 10 mg, gélule gastro-résistante
- OMEPRAZOLE EG 20 mg, gélule gastro-résistante

Le catalogue est volontairement limité dans cette première version afin de valider l’ensemble du pipeline avant son extension.

## Stack technique

### Application

- Python
- Streamlit

### IA et RAG

- Groq API
- Sentence Transformers
- `intfloat/multilingual-e5-small`
- FAISS

### OCR

- RapidOCR
- ONNX Runtime
- OpenCV

### Traitement des données

- Requests
- BeautifulSoup
- NumPy

### Déploiement

- Streamlit Community Cloud
- Python 3.12

## Structure du projet

```text
Pharmora/
│
├── app.py
├── requirements.txt
├── packages.txt
├── .env.example
│
├── .streamlit/
│   └── config.toml
│
├── assets/
│
├── data/
│   ├── catalog/
│   ├── documents/
│   ├── chunks/
│   ├── index/
│   └── raw/
│
└── src/
    ├── application/
    ├── catalog/
    ├── conversation/
    ├── evaluation/
    ├── ingestion/
    ├── processing/
    ├── rag/
    ├── retrieval/
    └── vision/
```

L’architecture est volontairement modulaire afin de permettre l’évolution indépendante des composants OCR, retrieval, RAG, conversation et interface utilisateur.

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/msamgaz4504-cmd/Pharmora.git
cd Pharmora
```

### 2. Créer un environnement virtuel

```bash
python -m venv .venv
```

Sous Windows :

```powershell
.\.venv\Scripts\Activate.ps1
```

Sous Linux ou macOS :

```bash
source .venv/bin/activate
```

### 3. Installer les dépendances

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Configuration

Créer un fichier `.env` à la racine du projet à partir de `.env.example`.

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
```

Le fichier `.env` contient des informations sensibles et ne doit jamais être versionné.

Pour le déploiement Streamlit, les secrets sont configurés directement dans Streamlit Community Cloud.

## Lancement

```bash
streamlit run app.py
```

L’application sera ensuite accessible localement sur :

```text
http://localhost:8501
```

## Déploiement

Pharmora est déployé avec Streamlit Community Cloud.

La version déployée utilise Python 3.12.

Les dépendances Python sont définies dans :

```text
requirements.txt
```

Les dépendances système Linux nécessaires à OpenCV sont définies dans :

```text
packages.txt
```

La configuration Streamlit est définie dans :

```text
.streamlit/config.toml
```

Les secrets nécessaires à l’application sont configurés directement dans Streamlit Community Cloud et ne sont pas stockés dans le dépôt GitHub.

## Sécurité et périmètre

Pharmora est conçu comme un outil d’information pharmaceutique documentaire.

L’application n’a pas pour objectif de :

- établir un diagnostic
- prescrire un traitement
- recommander de commencer un traitement
- recommander l’arrêt ou la modification d’un traitement
- modifier une posologie
- prendre une décision médicale personnalisée
- remplacer un médecin ou un pharmacien

Les demandes nécessitant une décision médicale personnalisée sont gérées par des garde-fous applicatifs.

## Validation actuelle

La V1 de Pharmora a été testée sur plusieurs niveaux :

- validation du catalogue pharmaceutique
- validation du corpus documentaire
- validation du chunking
- validation de l’index FAISS
- tests du retrieval
- tests du pipeline RAG
- tests des garde-fous
- tests de la gestion conversationnelle
- tests OCR
- tests d’identification de médicaments à partir d’images
- tests du workflow image → médicament → conversation → RAG
- tests des cas `resolved`, `ambiguous` et `not_found`
- validation du déploiement Streamlit

## Limites actuelles

Cette version constitue une première version fonctionnelle et évolutive.

Les principales limites actuelles sont :

- catalogue volontairement limité à 15 spécialités
- ressources limitées dans l’environnement Streamlit Community Cloud
- corpus pharmaceutique encore limité

## Roadmap

Les prochaines évolutions prévues incluent :

- élargissement du catalogue pharmaceutique
- automatisation de l’ingestion de nouveaux médicaments
- amélioration du grounding
- amélioration du retrieval
- amélioration de l’évaluation automatique
- amélioration de l’OCR sur les images difficiles
- optimisation des performances
- monitoring et observabilité
- amélioration continue de l’expérience utilisateur

## Statut du projet

Pharmora est actuellement en version V1 fonctionnelle et déployée.

La branche `main` contient la version stable et déployable de l’application.

Les futures évolutions sont développées et testées avant leur intégration dans la version stable.

## Avertissement

Pharmora fournit des informations documentaires basées sur des sources pharmaceutiques officielles.

L’application ne remplace pas un médecin, un pharmacien ou tout autre professionnel de santé.

## Auteur

Meryem Samgaz  
Étudiante ingénieure en Génie Informatique et Intelligence Artificielle — ENSA Safi
