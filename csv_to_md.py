import csv
import os
import re
from openai import OpenAI
import traceback
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Récupérer la clé API depuis les variables d'environnement
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("ERREUR: La variable d'environnement OPENAI_API_KEY n'est pas définie.")
    # Vous pouvez décider de quitter ou de continuer sans raffinement GPT
    # OPENAI_API_KEY = None # Déjà géré plus loin, mais l'erreur est plus claire ici

# Get the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Define paths relative to the script's directory
csv_filename = os.path.join(script_dir, "syllabus_opt_mim.csv")
md_filename = os.path.join(script_dir, "specialisations_escp.md")

# Define headers exactly as they appear in the CSV to ensure correct mapping
# Note: Ensure these match the CSV header row exactly, including spaces or case.
headers = [
    "specialization code", "specialization title", "Number of hours thaught",
    "Number of ECTS ", # Note the space at the end of 'ECTS '
    "teaching subject", "teaching department",
    "Professor responsible", "Campus", "specialisation goals", "teaching method",
    "specialisation overview", "cognitive skills", "transferable skills",
    "Semester", "Comments"
]

# Mapping CSV headers to Markdown section titles (optional, for clarity)
markdown_sections = {
    "specialisation goals": "Objectifs de la Spécialisation",
    "teaching method": "Méthode Pédagogique",
    "specialisation overview": "Aperçu de la Spécialisation",
    "cognitive skills": "Compétences Cognitives",
    "transferable skills": "Compétences Transférables",
    "Comments": "Commentaires"
}

def format_multiline_text(text):
    """Helper function to format multiline text fields for Markdown."""
    if not text:
        return ""
    # Replace potential multiple newlines with paragraph breaks
    paragraphs = text.strip().split('\\n\\n') # Split by double newlines if present
    if len(paragraphs) == 1:
        paragraphs = text.strip().split('\n\n') # Try splitting by actual double newlines

    formatted_text = ""
    for para in paragraphs:
        lines = para.strip().split('\n')
        # Check if any line in the paragraph starts with a list marker or similar
        is_list_like = any(l.strip().startswith(('*', '-', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '<br/>', '•')) for l in lines)

        if is_list_like:
             # Assume it's already list-like or has specific formatting, keep as is but clean up <br/>
             formatted_text += para.replace('<br/>', '\n').strip() + "\n\n"
        else:
             # Treat as paragraphs or simple text block
             formatted_text += para.strip() + "\n\n" # Add double newline for paragraph break

    return formatted_text.strip() # Remove trailing newlines

# Nouvelle fonction pour valider le document final
def validate_markdown(csv_file, md_file):
    """
    Vérifie que le nombre de spécialisations dans le fichier Markdown correspond 
    au nombre d'entrées valides dans le fichier CSV.
    """
    # Compter les entrées dans le CSV
    csv_count = 0
    with open(csv_file, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            code = row.get("specialization code", "").strip()
            title = row.get("specialization title", "").strip()
            if code or title:  # Si l'une de ces valeurs existe, c'est une entrée valide
                csv_count += 1
    
    # Compter les spécialisations dans le fichier Markdown
    md_count = 0
    with open(md_file, 'r', encoding='utf-8') as mdfile:
        content = mdfile.read()
        # Recherche des titres de niveau 2 (spécialisations)
        md_count = len(re.findall(r'^## ', content, re.MULTILINE))
    
    print(f"\n--- Validation du document final ---")
    print(f"Nombre d'entrées dans le CSV : {csv_count}")
    print(f"Nombre de spécialisations dans le Markdown : {md_count}")
    
    if csv_count == md_count:
        print("✅ VALIDATION RÉUSSIE : Le nombre de spécialisations correspond.")
        return True
    else:
        print("❌ ERREUR DE VALIDATION : Le nombre de spécialisations ne correspond pas.")
        print(f"Différence : {abs(csv_count - md_count)} spécialisation(s) manquante(s) ou supplémentaire(s).")
        return False

# --- Fonction pour l'appel OpenAI ---
def refine_markdown_with_gpt(markdown_content, specialization_code="", specialization_title=""):
    """
    Utilise GPT-4.1 pour nettoyer, standardiser et améliorer le contenu Markdown
    d'une spécialisation spécifique.
    """
    if not OPENAI_API_KEY:
        print("WARN: Clé API OpenAI non disponible. Saut de l'étape de raffinement GPT.")
        return markdown_content # Retourner le contenu original si pas de clé

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        print(f"Client OpenAI initialisé pour le raffinement de la spécialisation {specialization_code or specialization_title or 'actuelle'}.")
    except Exception as e:
        print(f"Erreur lors de l'initialisation du client OpenAI: {e}")
        return markdown_content # Retourner l'original en cas d'erreur

    # Définir le modèle GPT-4.1 à utiliser
    model_id = "gpt-4.1-2025-04-14" 
    print(f"Utilisation du modèle GPT: {model_id}")

    # --- Prompt pour GPT-4.1 ---
    system_prompt = """
    Vous êtes un expert en structuration et nettoyage de documents Markdown destinés à servir de base de connaissances pour un LLM d'assistance aux étudiants ESCP. Votre objectif est de rendre le texte parfaitement clair, cohérent, standardisé et facile à parser.
    - **Nettoyez** : Supprimez toutes les balises HTML résiduelles (<br/>, &nbsp;, etc.), les caractères d'échappement superflus (\\n).
    - **Standardisez** : Assurez une structure identique pour chaque spécialisation (Titre H2, liste à puces pour les métadonnées, titres H3 pour les sections comme Objectifs, Aperçu, etc.). Utilisez des listes à puces Markdown standard (*) pour les énumérations. Séparez les paragraphes par une seule ligne vide.
    - **Clarifiez** : Reformulez légèrement si nécessaire pour une meilleure lisibilité, sans altérer le sens original. Assurez-vous que les listes sont bien formatées.
    - **Cohérence** : Vérifiez la cohérence des titres de section (Objectifs de la Spécialisation, Méthode Pédagogique, etc.).
    - **Formatage** : Utilisez le Markdown standard (gras **, italique *, listes *, etc.).
    - **Sortie** : Retournez UNIQUEMENT le document Markdown complet, propre et standardisé, sans aucun commentaire ou texte avant/après. Commencez directement par le titre H2.
    """
    
    identifier = f" ({specialization_code})" if specialization_code else ""
    
    user_prompt = f"""
    Voici le bloc Markdown pour la spécialisation "{specialization_title}{identifier}". Veuillez le nettoyer, le standardiser et l'optimiser conformément aux instructions système pour qu'il serve de base de connaissances fiable. Le contenu brut est :

    ```markdown
    {markdown_content}
    ```

    Retournez uniquement le Markdown raffiné pour cette spécialisation, en commençant par le titre H2.
    """

    try:
        content_length = len(markdown_content)
        print(f"Envoi du bloc de spécialisation ({content_length} caractères) à {model_id} pour raffinement...")
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1, # Très factuel pour le nettoyage
        )

        refined_content = response.choices[0].message.content
        print(f"Réponse de raffinement reçue de GPT pour la spécialisation ({len(refined_content)} caractères).")

        # Nettoyage potentiel de la sortie de l'API (enlever ```markdown etc.)
        if refined_content.strip().startswith("```markdown"):
             refined_content = refined_content.strip()[len("```markdown"):].strip()
        if refined_content.strip().startswith("```"):
             refined_content = refined_content.strip()[len("```"):].strip()
        if refined_content.strip().endswith("```"):
            refined_content = refined_content.strip()[:-len("```")].strip()
            
        return refined_content

    except Exception as e:
        print(f"ERREUR lors de l'appel API OpenAI pour le raffinement: {e}")
        traceback.print_exc()
        return markdown_content # Retourner l'original en cas d'échec

try:
    # Liste pour stocker toutes les spécialisations raffinées
    all_refined_specializations = []
    
    # Compteur de spécialisations traitées
    specialization_count = 0
    
    # Lire toutes les entrées du CSV d'abord
    csv_data = []
    with open(csv_filename, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        # Vérification basique des en-têtes
        if not reader.fieldnames or not all(h in reader.fieldnames for h in headers):
            print(f"Avertissement: Les en-têtes CSV ne correspondent pas aux en-têtes attendus.")
            print(f"Attendus: {headers}")
            print(f"Trouvés: {reader.fieldnames}")
        
        # Stocker les données CSV pour traitement individuel
        for row in reader:
            csv_data.append(row)
    
    print(f"Lecture terminée: {len(csv_data)} entrées trouvées dans le CSV.")
    
    # Traitement individuel de chaque spécialisation
    for row_number, row in enumerate(csv_data, start=2):  # Start from 2 because of header row
        # Get data, defaulting to empty string if key is missing or value is None
        data = {header: row.get(header, "").strip() for header in headers}
        
        code = data["specialization code"]
        title = data["specialization title"]
        
        # Skip empty rows if necessary (e.g., if title and code are missing)
        if not code and not title:
            print(f"Ignoré: Ligne {row_number} vide ou invalide.")
            continue
        
        print(f"\n--- Traitement de la spécialisation {code}: {title} ---")
        
        # Variable temporaire pour stocker le Markdown de cette spécialisation
        specialization_md = ""
        
        # Start writing the Markdown for the specialization
        specialization_md += f"## {title} ({code})\n\n"
        
        # Write key-value pairs
        specialization_md += f"*   **Code :** {code}\n"
        specialization_md += f"*   **Titre :** {title}\n"
        specialization_md += f"*   **Volume Horaire :** {data['Number of hours thaught']} heures\n"
        specialization_md += f"*   **Crédits ECTS :** {data['Number of ECTS ']}\n" # Note space in key
        specialization_md += f"*   **Matière :** {data['teaching subject']}\n"
        specialization_md += f"*   **Département :** {data['teaching department']}\n"
        specialization_md += f"*   **Professeur(s) Responsable(s) :** {data['Professor responsible']}\n"
        specialization_md += f"*   **Campus :** {data['Campus']}\n"
        specialization_md += f"*   **Semestre :** {data['Semester']}\n\n"
        
        # Write multi-line sections using the mapping
        for csv_header, md_title in markdown_sections.items():
            content = data.get(csv_header, "")
            if content: # Only write section if there is content
                specialization_md += f"### {md_title}\n"
                # Basic formatting attempts for multiline fields
                formatted_content = format_multiline_text(content)
                specialization_md += f"{formatted_content}\n\n"
        
        specialization_md += "---\n\n" # Separator between specializations
        
        # Raffiner ce bloc individuel avec GPT-4.1
        print(f"Envoi de la spécialisation {code} pour raffinement...")
        refined_specialization = refine_markdown_with_gpt(
            specialization_md, 
            specialization_code=code, 
            specialization_title=title
        )
        
        # Ajouter à notre liste de spécialisations raffinées
        all_refined_specializations.append(refined_specialization)
        specialization_count += 1
        
        print(f"Spécialisation {code} traitée et raffinée ({len(refined_specialization)} caractères).")
    
    # Écrire toutes les spécialisations raffinées dans le fichier final
    with open(md_filename, 'w', encoding='utf-8') as mdfile:
        # Write initial Markdown header
        mdfile.write("# Base de Connaissances des Spécialisations ESCP MiM\n\n")
        mdfile.write("Ce document contient les informations détaillées sur les différentes spécialisations proposées dans le cadre du Master in Management (MiM) à l'ESCP Business School.\n\n")
        mdfile.write("---\n\n")
        
        # Écrire toutes les spécialisations raffinées
        for refined_text in all_refined_specializations:
            mdfile.write(f"{refined_text}\n")
    
    print(f"\nTraitement terminé: {specialization_count} spécialisations traitées et écrites dans '{md_filename}'.")
    
    # Valider le document final
    validate_markdown(csv_filename, md_filename)

except FileNotFoundError:
    print(f"Error: Input file not found. Make sure '{csv_filename}' exists relative to the script's execution directory.")
except Exception as e:
    print(f"An error occurred: {e}")
    traceback.print_exc() 