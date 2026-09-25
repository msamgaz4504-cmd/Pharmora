# Pharmora

Pharmora est un assistant d’information pharmaceutique basé sur une architecture RAG, conçu pour fournir des réponses claires et sourcées à partir de documents pharmaceutiques officiels.

L’application permet d’identifier un médicament par recherche textuelle ou à partir d’une photo de sa boîte, puis de poser des questions contextualisées sur ce médicament.

## Fonctionnalités principales

- Recherche de médicaments par nom, dosage et forme pharmaceutique
- Identification d’un médicament à partir d’une photo de boîte
- Extraction OCR locale avec PaddleOCR
- Identification contrôlée à partir d’un catalogue pharmaceutique
- Fiche structurée du médicament sélectionné
- Questions/réponses basées sur les RCP et notices
- Retrieval sémantique avec embeddings multilingues et FAISS
- Réécriture automatique des requêtes lorsque le contexte documentaire est insuffisant
- Gestion d’un historique conversationnel lié au médicament actif
- Réponses accompagnées de références vers les sources utilisées
- Gestion des cas ambigus ou non reconnus
- Garde-fous pour éviter les décisions médicales personnalisées

## Principe de fonctionnement

Pharmora sépare plusieurs responsabilités afin de conserver une architecture claire, modulaire et évolutive.

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
Sélection des preuves
        ↓
Génération de la réponse
        ↓
Sources
```

Pour l’identification à partir d’une image :

```text
Photo de la boîte
        ↓
PaddleOCR
        ↓
Extraction du texte
        ↓
Nom + dosage + forme
        ↓
Catalogue
        ↓
Identification du médicament
```

L’OCR ne décide pas directement de l’identité du médicament. Le texte extrait est utilisé pour retrouver une spécialité dans le catalogue pharmaceutique contrôlé.

## Architecture RAG

Le corpus documentaire est construit à partir de documents pharmaceutiques structurés.

### Pipeline offline

```text
Sources pharmaceutiques
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
Validation des citations
```

Le retrieval repose sur des embeddings multilingues E5 associés à un index FAISS.

## Stack technique

### Application

- Python
- Streamlit

### IA et RAG

- Groq API
- Sentence Transformers
- `intfloat/multilingual-e5-small`
- FAISS

### Vision et OCR

- PaddleOCR
- PaddlePaddle

### Traitement des données

- Requests
- BeautifulSoup
- NumPy

### Sources pharmaceutiques

- Base de données publique des médicaments
- Résumés des Caractéristiques du Produit
- Notices pharmaceutiques

## Structure générale

```text
Pharmora/
│
├── app.py
├── requirements.txt
├── .env.example
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
git clone <URL_DU_DEPOT>
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

## Lancement

```bash
streamlit run app.py
```

L’application sera ensuite accessible localement sur :

```text
http://localhost:8501
```

## Sécurité et périmètre

Pharmora est conçu comme un outil d’information pharmaceutique documentaire.

L’application n’a pas pour objectif de :

- établir un diagnostic
- prescrire un traitement
- recommander l’arrêt ou la modification d’un traitement
- prendre une décision médicale personnalisée
- remplacer un médecin ou un pharmacien

Les demandes nécessitant une décision médicale personnalisée sont gérées par des garde-fous applicatifs.

## Validation actuelle

La V1 de Pharmora a été testée sur plusieurs niveaux :

- validation du corpus documentaire
- validation du chunking
- validation de l’index FAISS
- tests du retrieval
- tests du pipeline RAG
- tests des garde-fous
- tests de la gestion conversationnelle
- tests d’identification OCR
- tests d’identification de médicaments à partir d’images
- tests du workflow image → médicament → conversation → RAG
- tests des cas `resolved`, `ambiguous` et `not_found`

## Limites actuelles

Cette version constitue une première version fonctionnelle et évolutive.

Les principales limites actuelles sont :

- catalogue volontairement limité
- dépendance à une API LLM externe
- qualité de l’OCR dépendante de la qualité de l’image fournie
- validation du grounding encore améliorable
- optimisation nécessaire pour les environnements cloud à ressources limitées
- couverture fonctionnelle encore volontairement limitée à une première version

## Roadmap

Les prochaines évolutions prévues incluent :

- élargissement du corpus pharmaceutique
- amélioration du grounding des réponses
- amélioration du retrieval
- amélioration de l’évaluation automatique du système
- optimisation de l’OCR
- meilleure gestion des images difficiles
- monitoring et observabilité
- ajout de tests automatisés supplémentaires
- optimisation des performances pour le déploiement cloud
- amélioration continue de l’expérience utilisateur
- extension progressive des fonctionnalités de l’assistant

## Statut du projet

Pharmora est actuellement en version V1.

La branche `main` est destinée à conserver une version stable et déployable de l’application.

Les futures évolutions pourront être développées sur des branches dédiées avant leur intégration dans la version stable.

## Avertissement

Pharmora fournit des informations documentaires basées sur des sources pharmaceutiques.

L’application ne remplace pas un médecin, un pharmacien ou tout autre professionnel de santé.

## Auteur

Meryem Samgaz  
Étudiante ingénieure en Génie Informatique et Intelligence Artificielle — ENSA Safi