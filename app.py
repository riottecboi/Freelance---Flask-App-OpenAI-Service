from flask import Flask, render_template, request, redirect, url_for, session
import os
import csv
import PyPDF2
from openai import OpenAI
from functools import wraps

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'secretsessionencryption' # Secret key for session encryption

# Créer le dossier 'uploads' s'il n'existe pas
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

users = {
    'user@example.com': 'password123',
    'user2@example.com': 'password123'
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def check_auth(username, password):
    """This function checks if a username and password combination is valid."""
    return username in users and users[username] == password

def load_text_from_file(file_path):
    if file_path.lower().endswith('.pdf'):
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ''
                for page in reader.pages:
                    extracted_text = page.extract_text()
                    if extracted_text:
                        text += extracted_text + '\n'
                return text.strip()
        except Exception as e:
            print(f"Erreur lors de l'extraction du texte du PDF : {e}")
            return None
    else:
        raise ValueError("Format de fichier non pris en charge. Veuillez utiliser un fichier PDF.")


def extract_cv_data(cv_text, api_key):
    if not cv_text:
        return []
    client = OpenAI(api_key=api_key)

    questions = [
        "Quel est le nom complet du candidat? (donne moi la reponse directement sans ecrire aucun texte ni avant ni apres)",
        "Quelle est l'adresse du candidat? (donne moi la reponse directement sans ecrire aucun texte ni avant ni apres)",
        "Quel est le numéro de téléphone du candidat (donne moi la reponse directement sans ecrire aucun texte ni avant ni apres)?",
        "Quelle est l'adresse email du candidat? (donne moi la reponse directement sans ecrire aucun texte ni avant ni apres)",
        "Quels sont les liens vers les profils professionnels en ligne du candidat?(donne moi la reponse directement sous la forme de tirets sans ecrire aucun texte ni avant ni apres)",
        "Quelle est l'expérience professionnelle du candidat? (donne moi la reponse directement sous la forme de tirets sans ecrire aucun texte ni avant ni apres)",
        "Quelle est la formation du candidat (donne moi la reponse directement sous la forme de tirets sans ecrire aucun texte ni avant ni apres)?",
        "Quelles sont les compétences du candidat en bref(donne moi la reponse directement sous la forme de tirets sans ecrire aucun texte ni avant ni apres)?",
        "Quel est le nombre total d'années d'expérience profesionnels seulement ? (retourne moi un entier, pas de texte)"
    ]

    extracted_data = []

    try:
        for question in questions:
            response = client.chat.completions.create(
                        messages=[
                            {
                                "role": "assistant",
                                "content": f"Question: {question}\n\nCV:\n{cv_text}\n\nRéponse:",
                            }
                        ],
                        model="gpt-4",
                    )
            answer = response.choices[0].message.content.strip()
            extracted_data.append(answer)
    except Exception as e:
        print(f"Erreur lors de la communication avec l'API OpenAI : {e}")

    return extracted_data


def save_to_csv(cv_data, csv_file):
    if os.path.exists(csv_file):
        mode = 'a'
    else:
        mode = 'w'

    with open(csv_file, mode, newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if mode == 'w':
            writer.writerow(["Nom complet", "Adresse", "Numéro de téléphone", "Adresse email", "Profils professionnels en ligne", "Expérience professionnelle", "Formation", "Compétences", "Nombre d'années d'expérience"])
        writer.writerow(cv_data)


def lire_pdf(fichier):
    text = ''
    lecteur_pdf = PyPDF2.PdfReader(fichier.stream)
    for page in lecteur_pdf.pages:
        extracted_text = page.extract_text()
        if extracted_text:
            text += extracted_text + '\n'  # Ajouter un saut de ligne entre les pages
    return text.strip()


def analyser_offre_demploi(texte, openai_api_key):

    client = OpenAI(api_key="sk-Irf9zcB")
    response = client.chat.completions.create(
    model="gpt-3.5-turbo-0125",
    response_format={ "type": "json_object" },
    messages=[
    {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
    {"role": "user","content": f"sous la forme de JSON Analyse ce document d'offre d'emploi et extrais les informations suivantes : le poste, les compétences requises (nom du chamop json est 'competences_requises' sous forme d'une liste), le nombre d'années d'expérience nécessaires (nom du champ json est 'nbr_annees_experience' un entier):\n{texte}"}
  ]
)
    print(response.choices[0].message.content)
    return response.choices[0].message.content

@app.route('/menu', methods=['GET'])
@login_required
def menu():
    return render_template('menu.html')

######################## Tableau de bord utilisateur ########################

# Route pour la page de connexion
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # You can remove the authentication check from here since it's handled by the decorator
        # Vérification simple des identifiants
        if check_auth(email, password):
            session['logged_in'] = True
            session['username'] = email
            return redirect(url_for('menu'))
        else:
            return "Email ou mot de passe incorrect.", 401
    if 'logged_in' in session:
        return redirect(url_for('menu', next=request.url))
    return render_template('login-v2.html')

# Route pour la page principale après connexion
@app.route('/indexoffer')
@login_required
def indexoffer():
    return render_template('indexoffer.html')

@app.route('/upload', methods=['POST'])
def upload():
    # La même fonction pour gérer le téléchargement des fichiers
    file = request.files['file']
    # Assurez-vous d'ajouter la gestion d'erreur appropriée ici
    texte_pdf = lire_pdf(file)
    resultats = analyser_offre_demploi(texte_pdf,"sk-Irf9zcZisZ")
    print(resultats)
    return (resultats)

######################## Analyse de CV ########################
@app.route('/analyse', methods=['GET', 'POST'])
@login_required
def upload_and_display():
    data = []
    if request.method == 'POST':
        files = request.files.getlist('file')
        for file in files:
            if file and file.filename.lower().endswith('.pdf'):
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(file_path)
                cv_text = load_text_from_file(file_path)
                if cv_text:
                    cv_data = extract_cv_data(cv_text, "sk-")
                    save_to_csv(cv_data, 'cv_data.csv')
    try:
        with open('cv_data.csv', 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                data.append(row)
    except Exception as e:
        print(str(e))
        pass
    return render_template('analyse_index.html', data=data)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run()
