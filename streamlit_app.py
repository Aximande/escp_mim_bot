import streamlit as st
import openai
from openai import OpenAI
import os
import pandas as pd
from dotenv import load_dotenv
import datetime
import time
from PIL import Image
import base64
from pathlib import Path

# Configuration de la page Streamlit en premier
st.set_page_config(
    page_title="ESCP MiM Spécialisation Advisor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS simplifié qui fonctionne dans les deux modes
escp_colors = """
<style>
    /* Couleurs ESCP */
    :root {
        --escp-purple: #382B73;
        --escp-purple-light: #5D4F9C;
        --escp-gold: #F2C75C;
    }
    
    /* Styles généraux qui fonctionnent dans les deux modes */
    h1, h2, h3, h4, h5, h6 {
        color: var(--escp-purple);
    }
    
    /* Personnalisation des boutons */
    .stButton > button {
        background-color: var(--escp-purple);
        color: white;
        border: none;
        border-radius: 4px;
    }
    
    .stButton > button:hover {
        background-color: var(--escp-purple-light);
    }
    
    /* Ajustements pour le mode sombre (plus simples) */
    @media (prefers-color-scheme: dark) {
        h1, h2, h3, h4, h5, h6 {
            color: #8A7BC8;
        }
        
        section[data-testid="stSidebar"] {
            background-color: #1E1E2E;
        }
    }
</style>
"""

st.markdown(escp_colors, unsafe_allow_html=True)

# Chargement de la configuration
load_dotenv()

# Configuration de l'API OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Fonction pour charger et encoder l'image en base64
def get_img_as_base64(file_path):
    with open(file_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# Pour deux versions du logo (claire et sombre)
logo_light_path = "ESCP_LOGO_CMJN.png"
logo_dark_path = "ESCP_LOGO_CMJN.png"  # Logo alternatif pour fond sombre

try:
    logo_light_img = get_img_as_base64(logo_light_path)
    
    # Tenter de charger le logo pour mode sombre, sinon utiliser celui pour mode clair
    try:
        logo_dark_img = get_img_as_base64(logo_dark_path)
    except:
        logo_dark_img = logo_light_img
    
    # HTML avec détection du mode sombre
    logo_html = f'''
    <picture>
        <source srcset="data:image/png;base64,{logo_dark_img}" media="(prefers-color-scheme: dark)">
        <img src="data:image/png;base64,{logo_light_img}" alt="ESCP Logo" width="180">
    </picture>
    '''
except Exception as e:
    print(f"Erreur lors du chargement du logo: {e}")
    logo_html = '<div style="font-weight: bold; font-size: 24px; color: #382B73;">ESCP</div>'

# En-tête personnalisé avec logo ESCP
def display_header():
    # Utiliser une mise en page en colonnes native de Streamlit
    col1, col2 = st.columns([1, 3])
    
    with col1:
        # Afficher le logo directement avec st.image
        st.image("ESCP_LOGO_CMJN.png", width=150)
    
    with col2:
        st.title("Master in Management - Spécialisation Advisor")
        st.write("Trouvez la spécialisation idéale pour votre parcours à ESCP Business School")

# Afficher l'en-tête
display_header()

# Chargement du contexte du document
@st.cache_resource  # Cache pour éviter de recharger à chaque interaction
def load_knowledge_base():
    with open("specialisations_escp.md", "r", encoding="utf-8") as f:
        return f.read()

knowledge_base = load_knowledge_base()

# 1. Ajouter un dictionnaire de traduction pour tous les éléments d'interface
translations = {
    "Français": {
        "title": "Master in Management - Spécialisation Advisor",
        "subtitle": "Trouvez la spécialisation idéale pour votre parcours à ESCP Business School",
        "search_title": "Personnalisez votre recherche",
        "campus_label": "Campus",
        "semester_label": "Semestre",
        "teaching_language": "Langue d'enseignement",
        "interest_domains": "Domaines d'intérêt",
        "advanced_filters": "Filtres avancés",
        "teaching_method": "Méthode pédagogique",
        "career_goals": "Objectifs de carrière (facultatif)",
        "skills_to_develop": "Compétences à développer",
        "new_conversation": "Nouvelle conversation",
        "question_prompt": "Posez votre question sur les spécialisations...",
        "questions_suggested": "Questions suggérées pour commencer",
        "explore_options": "Explorer les options",
        "explore_specialization": "Approfondir une spécialisation",
        "compare_options": "Comparer des options",
        "thinking": "Je réfléchis...",
        "welcome_message": "👋 Bonjour! Je suis votre conseiller pour les spécialisations ESCP du Master in Management. Comment puis-je vous aider dans votre choix de spécialisation? Vous pouvez me poser des questions spécifiques ou me parler de vos intérêts et objectifs de carrière."
    },
    "English": {
        "title": "Master in Management - Specialization Advisor",
        "subtitle": "Find the ideal specialization for your journey at ESCP Business School",
        "search_title": "Customize your search",
        "campus_label": "Campus",
        "semester_label": "Semester",
        "teaching_language": "Teaching language",
        "interest_domains": "Areas of interest",
        "advanced_filters": "Advanced filters",
        "teaching_method": "Teaching method",
        "career_goals": "Career goals (optional)",
        "skills_to_develop": "Skills to develop",
        "new_conversation": "New conversation",
        "question_prompt": "Ask your question about specializations...",
        "questions_suggested": "Suggested questions to get started",
        "explore_options": "Explore options",
        "explore_specialization": "Explore a specialization",
        "compare_options": "Compare options",
        "thinking": "Thinking...",
        "welcome_message": "👋 Hello! I'm your ESCP Master in Management specialization advisor. How can I help you choose your specialization? You can ask specific questions or tell me about your interests and career goals."
    }
}

# Initialisation de la variable de langue
if 'language' not in st.session_state:
    st.session_state.language = "Français"

# Puis modifier la fonction t() pour gérer le cas où language n'est pas défini
def t(key):
    # Vérifier si language existe, sinon utiliser "Français" par défaut
    lang = st.session_state.get("language", "Français")
    if key in translations[lang]:
        return translations[lang][key]
    return key  # Fallback au cas où la clé n'existe pas

# Sidebar pour les filtres et les préférences
with st.sidebar:
    # Logo
    st.image("ESCP_LOGO_CMJN.png", width=150)
    st.markdown(f"### {t('title')}")
    st.divider()
    
    st.title(t('search_title'))
    
    # Sélecteur de langue (plus besoin de vérifier si language existe)
    language = st.radio("Langue / Language", ["Français", "English"], 
                       index=0 if st.session_state.language == "Français" else 1)
    
    if language != st.session_state.language:
        st.session_state.language = language
        # Réinitialiser la conversation si la langue change
        if 'messages' in st.session_state and st.session_state.messages and len(st.session_state.messages) > 1:
            if st.warning("Changer de langue réinitialisera la conversation. Continuer ?" if language == "Français" else "Changing language will reset the conversation. Continue?"):
                st.session_state.messages = []
                # Ajouter un nouveau message de bienvenue dans la bonne langue
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": t('welcome_message')
                })
                st.rerun()
    
    st.divider()
    
    # Filtres avec étiquettes traduites
    campuses = st.multiselect(t('campus_label'), ["Paris", "London", "Berlin", "Madrid", "Turin"])
    semesters = st.multiselect(t('semester_label'), ["Fall", "Spring"])
    languages = st.multiselect(t('teaching_language'), ["Français", "Anglais", "Bilingue"])
    domains = st.multiselect(t('interest_domains'), [
        "Finance", "Marketing", "Entrepreneurship", "Sustainability", 
        "Digital Transformation", "Consulting", "Project Management", "Others"
    ])
    
    # Filtres avancés traduits
    with st.expander(t('advanced_filters')):
        teaching_method = st.multiselect(t('teaching_method'), ["100% présentiel", "Blended", "100% en ligne"])
        career_goals = st.text_area(t('career_goals'))
        skills_focus = st.multiselect(t('skills_to_develop'), [
            "Analytiques", "Techniques", "Leadership", "Communication", 
            "Gestion de projet", "Entrepreneuriales", "Durables"
        ])
    
    # Bouton traduit
    if st.button(t('new_conversation')):
        st.session_state.messages = []
        if 'specialization_filter' in st.session_state:
            st.session_state.specialization_filter = []
        # Ajouter un message de bienvenue dans la bonne langue
        st.session_state.messages.append({
            "role": "assistant",
            "content": t('welcome_message')
        })
        st.rerun()
        
    # Pied de page avec mentions ESCP
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        <div style='text-align: center; color: #666; font-size: 0.8rem;'>
            <p>© ESCP Business School 2024</p>
            <p>Master in Management Programme</p>
        </div>
        """,
        unsafe_allow_html=True
    )

# Construction du contexte enrichi pour l'API
def create_enriched_context():
    # Créer un contexte qui inclut les filtres et préférences
    context_parts = ["Informations sur les préférences de l'étudiant:"]
    
    if campuses:
        context_parts.append(f"- Campus préférés: {', '.join(campuses)}")
    if semesters:
        context_parts.append(f"- Semestres préférés: {', '.join(semesters)}")
    if languages:
        context_parts.append(f"- Langues préférées: {', '.join(languages)}")
    if domains:
        context_parts.append(f"- Domaines d'intérêt: {', '.join(domains)}")
    if 'teaching_method' in locals() and teaching_method:
        context_parts.append(f"- Méthode pédagogique préférée: {', '.join(teaching_method)}")
    if 'career_goals' in locals() and career_goals:
        context_parts.append(f"- Objectifs de carrière: {career_goals}")
    if 'skills_focus' in locals() and skills_focus:
        context_parts.append(f"- Compétences à développer: {', '.join(skills_focus)}")
    
    # Ajouter l'historique récent des messages pour le contexte de conversation
    last_messages = st.session_state.messages[-5:] if len(st.session_state.messages) > 5 else st.session_state.messages
    for msg in last_messages:
        context_parts.append(f"{msg['role'].capitalize()}: {msg['content']}")
    
    return "\n".join(context_parts)

# Fonction pour générer la réponse
def generate_response(prompt, knowledge_base, user_context):
    with st.spinner(t('thinking')):
        try:
            # Construction des messages pour l'API avec la bonne langue
            if st.session_state.language == "Français":
                system_content = """Vous êtes le Conseiller en Spécialisations ESCP, un assistant expert dédié à aider les étudiants du Master in Management (MiM) à choisir leur spécialisation idéale. Votre base de connaissances contient les informations détaillées sur toutes les spécialisations disponibles à l'ESCP Business School.

OBJECTIF PRINCIPAL:
Guider les étudiants MiM dans leur processus de décision en fournissant des informations précises, personnalisées et nuancées sur les spécialisations qui correspondent le mieux à leurs intérêts, compétences et objectifs de carrière.

COMPORTEMENT:
- Soyez chaleureux et empathique, tout en restant professionnel - le choix d'une spécialisation est une décision importante.
- Adaptez votre communication au niveau de connaissance de l'étudiant - certains peuvent être en première année, d'autres en phase finale de décision.
- Répondez toujours en français.
- Ne vous inventez jamais d'informations - basez-vous uniquement sur le contenu de la base de connaissances.
- Si une information est manquante, reconnaissez-le clairement et suggérez à l'étudiant de contacter directement le responsable de la spécialisation concernée.

MÉTHODOLOGIE D'AIDE À LA DÉCISION:
1. EXPLORATION: Posez des questions sur les intérêts, compétences et aspirations professionnelles de l'étudiant pour mieux comprendre son profil.
2. RECOMMANDATION: Suggérez 2-3 spécialisations qui correspondent le mieux au profil identifié, en expliquant les raisons de ces recommandations.
3. COMPARAISON: Aidez l'étudiant à comparer les spécialisations, notamment en termes de contenu, campus, langue d'enseignement, méthodes pédagogiques et débouchés professionnels.
4. APPROFONDISSEMENT: Fournissez des détails spécifiques sur les cours, les compétences développées et les opportunités de carrière pour chaque spécialisation demandée."""
            else:
                system_content = """You are the ESCP Specialization Advisor, an expert assistant dedicated to helping Master in Management (MiM) students choose their ideal specialization. Your knowledge base contains detailed information on all specializations available at ESCP Business School.

MAIN OBJECTIVE:
Guide MiM students in their decision-making process by providing accurate, personalized, and nuanced information about the specializations that best match their interests, skills, and career goals.

BEHAVIOR:
- Be warm and empathetic while remaining professional - choosing a specialization is an important decision.
- Adapt your communication to the student's level of knowledge - some may be in their first year, others in their final decision phase.
- Always respond in English.
- Never invent information - rely solely on the content of the knowledge base.
- If information is missing, acknowledge it clearly and suggest that the student contact the specialization coordinator directly.

DECISION-MAKING METHODOLOGY:
1. EXPLORATION: Ask questions about the student's interests, skills, and professional aspirations to better understand their profile.
2. RECOMMENDATION: Suggest 2-3 specializations that best match the identified profile, explaining the reasons for these recommendations.
3. COMPARISON: Help the student compare specializations, particularly in terms of content, campus, teaching language, teaching methods, and career opportunities.
4. DEEP DIVE: Provide specific details about courses, skills developed, and career opportunities for each requested specialization."""
            
            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": f"Contexte utilisateur:\n{user_context}\n\nBase de connaissances sur les spécialisations ESCP:\n{knowledge_base}\n\nQuestion de l'étudiant: {prompt}"}
            ]
            
            # Appel à l'API GPT-4.1
            response = client.chat.completions.create(
                model="gpt-4.1-2025-04-14",
                messages=messages,
                temperature=0.1,
                max_tokens=8000,
                top_p=0.95,
                frequency_penalty=0,
                presence_penalty=0
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            error_msg = "Désolé, une erreur s'est produite: " if st.session_state.language == "Français" else "Sorry, an error occurred: "
            return f"{error_msg}{str(e)}"

# Extraction et utilisation des spécialisations mentionnées dans la conversation
if "specialization_mentions" not in st.session_state:
    st.session_state.specialization_mentions = {}

def extract_specialization_mentions(text):
    # Regex pour extraire les codes de spécialisation (OPxx)
    import re
    pattern = r'\b(OP\d+[A-Z]?)\b'
    matches = re.findall(pattern, text)
    
    # Mettre à jour les mentions
    for code in matches:
        if code in st.session_state.specialization_mentions:
            st.session_state.specialization_mentions[code] += 1
        else:
            st.session_state.specialization_mentions[code] = 1

# Extraire les mentions des spécialisations de la dernière réponse
if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
    extract_specialization_mentions(st.session_state.messages[-1]["content"])

# Afficher les spécialisations les plus discutées dans une section en bas de page
if st.session_state.specialization_mentions:
    with st.expander("Spécialisations les plus discutées", expanded=False):
        sorted_mentions = dict(sorted(st.session_state.specialization_mentions.items(), 
                              key=lambda item: item[1], reverse=True))
        
        cols = st.columns(min(3, len(sorted_mentions)))
        for i, (code, count) in enumerate(list(sorted_mentions.items())[:3]):
            # Trouver le titre de la spécialisation dans la base de connaissances
            import re
            title_match = re.search(f"{code}[^\n]*\*\*Titre :\*\* ([^\n]*)", knowledge_base)
            title = title_match.group(1) if title_match else "Spécialisation inconnue"
            
            with cols[i]:
                st.metric(f"Code: {code}", title, f"Mentionnée {count} fois")
                if st.button(f"Détails sur {code}", key=f"detail_{code}"):
                    # Simuler une question sur cette spécialisation
                    new_prompt = f"Donne-moi tous les détails sur la spécialisation {code}."
                    st.session_state.messages.append({"role": "user", "content": new_prompt})
                    st.rerun()

# Fonction d'exportation de la conversation
def export_conversation():
    conversation_text = "# Conversation avec le Conseiller en Spécialisations ESCP\n\n"
    conversation_text += f"Date: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
    
    for msg in st.session_state.messages:
        role = "Étudiant" if msg["role"] == "user" else "Conseiller"
        conversation_text += f"**{role}**: {msg['content']}\n\n"
    
    return conversation_text

# Ajout d'un bouton d'exportation dans la sidebar
with st.sidebar:
    if st.download_button(
        label="Exporter la conversation",
        data=export_conversation(),
        file_name=f"ESCP_specialisations_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown",
    ):
        st.success("Conversation exportée avec succès!")

# Fonctionnalité de feedback en fin de conversation
with st.sidebar:
    st.divider()
    st.subheader("Évaluez votre expérience")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👍 Utile"):
            st.session_state.feedback = "positive"
            st.success("Merci pour votre feedback positif!")
    with col2:
        if st.button("👎 À améliorer"):
            st.session_state.feedback = "negative"
            st.text_area("Comment pouvons-nous améliorer?", key="feedback_text")
            if st.button("Envoyer"):
                st.success("Merci pour vos suggestions!")

# Conteneur principal avec style
main_container = st.container()
with main_container:
    # Initialisation de l'historique des messages
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # Message de bienvenue initial
        system_welcome = {
            "role": "assistant",
            "content": t('welcome_message')
        }
        st.session_state.messages.append(system_welcome)

    # Traitement de la réponse si il y a une nouvelle question
    if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user":
        user_context = create_enriched_context()
        response = generate_response(st.session_state.messages[-1]["content"], knowledge_base, user_context)
        
        # Ajouter la réponse à l'historique
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Affichage de l'historique complet des messages (après ajout de la nouvelle réponse s'il y en a une)
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Questions suggérées (seulement si peu de messages)
    if len(st.session_state.messages) <= 1:  # Si c'est le début de la conversation
        st.markdown(f"""
        <div style='background-color: rgba(56, 43, 115, 0.05); padding: 1rem; border-radius: 10px; margin-bottom: 1rem; border: 1px solid rgba(56, 43, 115, 0.1);'>
            <h3 style='color: #382B73; margin-top: 0;'>{t('questions_suggested')}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Questions traduites selon la langue
        if st.session_state.language == "Français":
            question_categories = {
                "Explorer les options": [
                    "Quelles spécialisations sont disponibles sur le campus de Paris ?",
                    "Quelles options existent en finance ?",
                    "Présentez-moi les spécialisations en développement durable.",
                ],
                "Approfondir une spécialisation": [
                    "Que propose la spécialisation International Business and Sustainability (OP01) ?",
                    "Quels sont les objectifs d'Option E (OP24) ?",
                    "Quels cours sont proposés dans Digital Project Management ?",
                ],
                "Comparer des options": [
                    "Quelles sont les différences entre Digital Project Management 1 et 2 ?",
                    "Comparez les spécialisations en Marketing.",
                ]
            }
        else:  # English
            question_categories = {
                "Explore options": [
                    "Which specializations are available on the Paris campus?",
                    "What options exist in finance?",
                    "Show me the sustainability specializations.",
                ],
                "Explore a specialization": [
                    "What does the International Business and Sustainability (OP01) specialization offer?",
                    "What are the objectives of Option E (OP24)?",
                    "What courses are offered in Digital Project Management?",
                ],
                "Compare options": [
                    "What are the differences between Digital Project Management 1 and 2?",
                    "Compare the Marketing specializations.",
                ]
            }
        
        # Afficher les catégories de questions dans des colonnes
        cols = st.columns(len(question_categories))
        
        for i, (category, questions) in enumerate(question_categories.items()):
            with cols[i]:
                st.markdown(f"<h4 style='color: #382B73;'>{category}</h4>", unsafe_allow_html=True)
                for question in questions:
                    if st.button(question, key=f"q_{i}_{question}"):
                        # Simuler une question utilisateur quand un bouton est cliqué
                        st.session_state.messages.append({"role": "user", "content": question})
                        st.rerun()

    # Input de l'utilisateur - maintenant APRÈS l'affichage de tout le reste
    if prompt := st.chat_input(t('question_prompt')):  # Utiliser la traduction pour le placeholder
        # Ajouter le message de l'utilisateur à l'historique
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Recharger la page pour traiter la réponse
        st.rerun()
