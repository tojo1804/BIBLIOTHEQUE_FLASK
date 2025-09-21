from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secretkey"
UPLOAD_FOLDER = os.path.join('static', 'images')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DB_NAME = "bibliotheque.db"

# --- Création automatique de la base + tables ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Table produits si pas déjà créée
    c.execute('''CREATE TABLE IF NOT EXISTS produits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nom_de_produit TEXT,
                    categorie TEXT,
                    prix REAL,
                    description TEXT,
                    image TEXT
                )''')
    # Table users
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nom TEXT,
                    prenom TEXT,
                    email TEXT UNIQUE,
                    adresse TEXT,
                    password TEXT,
                    is_admin INTEGER DEFAULT 0
                )''')

    # Table commandes si pas déjà créée
    c.execute('''CREATE TABLE IF NOT EXISTS commandes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                nom TEXT,
                prenom TEXT,
                email TEXT,
                adresse TEXT,
                phone TEXT,
                produit TEXT,
                quantite INTEGER,
                total REAL
                )''')
    # Dans init_db()
    c.execute('''CREATE TABLE IF NOT EXISTS apropos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image TEXT,
                texte TEXT)''')




    conn.commit()
    conn.close()

init_db()

# --- Créer superadmin une seule fois ---
def create_superadmin():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", ("admin@site.com",))
    if not c.fetchone():
        password = generate_password_hash("1804653")  # mot de passe superadmin
        c.execute("INSERT INTO users (nom, prenom, email, adresse, password, is_admin) VALUES (?,?,?,?,?,?)",
                  ("Super", "Admin", "admin@site.com", "Adresse Admin", password, 1))
        conn.commit()
    conn.close()

create_superadmin()

# --- Page d'inscription ---
@app.route('/create_user', methods=['GET','POST'])
def create_user():
    if request.method == 'POST':
        nom = request.form['nom']
        prenom = request.form['prenom']
        email = request.form['email']
        adresse = request.form['adresse']
        password = request.form['password']
        confirm = request.form['confirm']
        if password != confirm:
            flash("Les mots de passe ne correspondent pas")
            return redirect(url_for('create_user'))
        hashed = generate_password_hash(password)
        try:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO users (nom, prenom, email, adresse, password) VALUES (?,?,?,?,?)",
                      (nom, prenom, email, adresse, hashed))
            conn.commit()
            conn.close()
            flash("Compte créé avec succès ! Vous pouvez vous connecter.")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Cet email existe déjà")
            return redirect(url_for('create_user'))
    return render_template('create_user.html')

# --- Page login ---
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, password, is_admin FROM users WHERE email=?", (email,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['is_admin'] = bool(user[2])
            session['email'] = email
            flash("Connecté avec succès")
            return redirect(url_for('index'))
        else:
            flash("Email ou mot de passe incorrect")
            return redirect(url_for('login'))
    return render_template('login.html')

# --- Déconnexion ---
@app.route('/logout')
def logout():
    session.clear()
    flash("Déconnecté")
    return redirect(url_for('index'))

# Index
@app.route('/')
def index():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM produits")   # ← corrigé
    produits = cursor.fetchall()
    conn.close()
    return render_template('index.html', produits=produits)

# --- Page admin sécurisée ---
@app.route('/admin', methods=['GET','POST'])
def admin():
    if not session.get('is_admin'):
        flash("Accès refusé.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        nom = request.form['nom_de_produit']
        categorie = request.form['categorie']
        prix = request.form['prix']
        description = request.form['description']
        image_file = request.files['image_file']
        image_path = image_file.filename
        image_file.save(os.path.join('static/images', image_path))

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO produits (nom_de_produit,categorie,prix,description,image) VALUES (?,?,?,?,?)",
                  (nom,categorie,prix,description,image_path))
        conn.commit()
        conn.close()
        flash("Produit ajouté avec succès")
        return redirect(url_for('admin'))

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM produits")   # ← corrigé
    produits = c.fetchall()
    conn.close()
    return render_template('admin.html', produits=produits)

# Supprimer un produit
@app.route('/delete/<int:produit_id>')
def delete_produit(produit_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM produits WHERE id=?", (produit_id,))  # ← corrigé
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

# Modifier un produit
@app.route('/edit/<int:produit_id>', methods=['GET', 'POST'])
def edit_produit(produit_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if request.method == 'POST':
        nom = request.form['nom_de_produit']
        categorie = request.form['categorie']
        prix = float(request.form['prix'])
        description = request.form['description']

        file = request.files['image_file']
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cursor.execute("UPDATE produits SET nom_de_produit=?, categorie=?, prix=?, description=?, image=? WHERE id=?",
                           (nom, categorie, prix, description, filename, produit_id))
        else:
            cursor.execute("UPDATE produits SET nom_de_produit=?, categorie=?, prix=?, description=? WHERE id=?",
                           (nom, categorie, prix, description, produit_id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))
    else:
        cursor.execute("SELECT * FROM produits WHERE id=?", (produit_id,))  # ← corrigé
        produit = cursor.fetchone()
        conn.close()
        return render_template('edit.html', produit=produit)

# Page catégorie
@app.route('/categorie/<string:categorie>')
def categorie(categorie):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM produits WHERE categorie=?", (categorie,))  # ← corrigé
    produits = cursor.fetchall()
    conn.close()
    return render_template('categorie.html', produits=produits, categorie=categorie)

# Page recherche
@app.route('/recherche', methods=['GET'])
def recherche():
    query = request.args.get('q')  # Récupère le texte de la barre de recherche
    if not query:
        return redirect(url_for('index'))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM produits WHERE nom_de_produit LIKE ? OR description LIKE ?", 
                   (f'%{query}%', f'%{query}%'))  # ← corrigé
    produits = cursor.fetchall()
    conn.close()
    return render_template('recherche.html', produits=produits, query=query)

# Page détail produit
@app.route('/produit/<int:produit_id>', methods=['GET', 'POST'])
def produit_detail(produit_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM produits WHERE id=?", (produit_id,))  # ← corrigé
    produit = cursor.fetchone()
    conn.close()

    if not produit:
        return "Produit non trouvé", 404

    if request.method == 'POST':
        quantite = int(request.form['quantite'])
        flash(f"{quantite} x {produit[1]} ajouté au panier !")
        return redirect(url_for('produit_detail', produit_id=produit_id))

    return render_template('produit.html', produit=produit)
#resaka cart ny ato 
# Ajout de la table panier
def init_panier():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Crée la table panier si elle n'existe pas
    c.execute('''
        CREATE TABLE IF NOT EXISTS panier (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            produit_id INTEGER
        )
    ''')
    # Vérifie si la colonne quantite existe déjà
    c.execute("PRAGMA table_info(panier)")
    columns = [col[1] for col in c.fetchall()]
    if 'quantite' not in columns:
        c.execute("ALTER TABLE panier ADD COLUMN quantite INTEGER DEFAULT 1")
    conn.commit()
    conn.close()

init_panier()




#add cart ou ajouter dans le panier
@app.route('/add_to_cart/<int:produit_id>')
def add_to_cart(produit_id):
    if 'user_id' not in session:
        flash("Veuillez vous connecter pour commander.")
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, quantite FROM panier WHERE user_id=? AND produit_id=?", (user_id, produit_id))
    row = c.fetchone()
    if row:
        # Augmenter la quantité
        c.execute("UPDATE panier SET quantite=? WHERE id=?", (row[1]+1, row[0]))
        flash("Quantité mise à jour dans le panier.")
    else:
        c.execute("INSERT INTO panier (user_id, produit_id, quantite) VALUES (?,?,1)", (user_id, produit_id))
        flash("Produit ajouté au panier.")
    conn.commit()
    conn.close()
    return redirect(url_for('produit_detail', produit_id=produit_id))



@app.before_request
def load_cart_count():
    if 'user_id' in session:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM panier WHERE user_id=?", (session['user_id'],))
        count = c.fetchone()[0]
        session['cart_count'] = count
        conn.close()
    else:
        session['cart_count'] = 0









#voir le panier 
# @app.route('/cart')
# def view_cart():
#     if 'user_id' not in session:
#         flash("Connectez-vous pour voir votre panier.")
#         return redirect(url_for('login'))

#     conn = sqlite3.connect(DB_NAME)
#     c = conn.cursor()
#     c.execute("""SELECT p.id, p.nom_de_produit, p.prix, p.image 
#                  FROM produits p 
#                  JOIN panier c2 ON p.id=c2.produit_id 
#                  WHERE c2.user_id=?""", (session['user_id'],))
#     produits = c.fetchall()
#     conn.close()
#     return render_template('cart.html', produits=produits)
@app.route('/cart')
def view_cart():
    if 'user_id' not in session:
        flash("Connectez-vous pour voir votre panier.")
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT c2.id, p.nom_de_produit, p.prix, p.image, c2.quantite
        FROM produits p
        JOIN panier c2 ON p.id = c2.produit_id
        WHERE c2.user_id=?
    """, (session['user_id'],))
    produits = c.fetchall()

    total_general = sum(float(p[2]) * int(p[4]) for p in produits)  # Calcul côté Flask

    conn.close()
    return render_template('cart.html', produits=produits, total_general=total_general)










@app.before_request
def load_cart_count():
    if 'user_id' in session:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM panier WHERE user_id=?", (session['user_id'],))
        count = c.fetchone()[0]
        session['cart_count'] = count
        conn.close()
    else:
        session['cart_count'] = 0



# Supprimer un produit du panier
@app.route('/delete_cart/<int:panier_id>')
def delete_cart(panier_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM panier WHERE id=?", (panier_id,))
    conn.commit()
    conn.close()
    flash("Produit supprimé du panier.")
    return redirect(url_for('view_cart'))

# Modifier la quantité
@app.route('/update_cart/<int:panier_id>', methods=['POST'])
def update_cart(panier_id):
    qte = int(request.form['quantite'])
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if qte > 0:
        c.execute("UPDATE panier SET quantite=? WHERE id=?", (qte, panier_id))
    else:
        c.execute("DELETE FROM panier WHERE id=?", (panier_id,))
    conn.commit()
    conn.close()
    flash("Quantité mise à jour.")
    return redirect(url_for('view_cart'))

# Checkout
# @app.route('/checkout', methods=['GET','POST'])
# def checkout():
#     if 'user_id' not in session:
#         flash("Connectez-vous pour effectuer le paiement.")
#         return redirect(url_for('login'))

#     conn = sqlite3.connect(DB_NAME)
#     c = conn.cursor()

#     # Récupérer les produits du panier
#     c.execute("""
#         SELECT c2.id, p.nom_de_produit, p.prix, c2.quantite
#         FROM produits p
#         JOIN panier c2 ON p.id = c2.produit_id
#         WHERE c2.user_id=?
#     """, (session['user_id'],))
#     produits = c.fetchall()

#     total_general = sum(float(p[2]) * int(p[3]) for p in produits)
#     conn.close()

#     # Si panier vide
#     if not produits:
#         flash("Votre panier est vide.")
#         return redirect(url_for('index'))

#     # Redirection vers formulaire de livraison
#     return render_template('checkout.html', produits=produits, total_general=total_general)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        flash("Connectez-vous pour compléter la commande.")
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT nom, prenom, email, adresse FROM users WHERE id=?", (session['user_id'],))
    user = c.fetchone()
    conn.close()

    # Convertir le tuple en dictionnaire pour Jinja
    user_dict = {
        "nom": user[0],
        "prenom": user[1],
        "email": user[2],
        "adresse": user[3]
    }

    return render_template('checkout.html', user=user_dict)














@app.route('/finalize_order', methods=['POST'])
def finalize_order():
    if 'user_id' not in session:
        flash("Connectez-vous pour passer la commande.")
        return redirect(url_for('login'))

    user_id = session['user_id']
    phone = request.form['phone']

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Récupérer les infos user
    c.execute("SELECT nom, prenom, email, adresse FROM users WHERE id=?", (user_id,))
    user_info = c.fetchone()
    nom, prenom, email, adresse = user_info

    # Récupérer produits du panier
    c.execute("""
        SELECT p.nom_de_produit, p.prix, c2.quantite
        FROM produits p
        JOIN panier c2 ON p.id = c2.produit_id
        WHERE c2.user_id=?
    """, (user_id,))
    produits = c.fetchall()

    # Insérer chaque produit comme commande
    for p in produits:
        produit_nom = p[0]
        prix = float(p[1])
        quantite = int(p[2])
        total = prix * quantite
        c.execute("""
            INSERT INTO commandes (user_id, nom, prenom, email, adresse, phone, produit, quantite, total)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (user_id, nom, prenom, email, adresse, phone, produit_nom, quantite, total))

    # Vider le panier
    c.execute("DELETE FROM panier WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

    flash("Commande passée avec succès !")
    return redirect(url_for('index'))

@app.route('/admin_orders')
def admin_orders():
    if not session.get('is_admin'):
        flash("Accès refusé.")
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM commandes ORDER BY id DESC")
    commandes = c.fetchall()
    conn.close()
    return render_template('admin_orders.html', commandes=commandes)




@app.route('/delete_order/<int:commande_id>')
def delete_order(commande_id):
    if not session.get('is_admin'):
        flash("Accès refusé.")
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM commandes WHERE id=?", (commande_id,))
    conn.commit()
    conn.close()

    flash("Commande supprimée avec succès.")
    return redirect(url_for('admin_orders'))

# admin apropos
@app.route('/admin_apropos', methods=['GET', 'POST'])
def admin_apropos():
    if not session.get('is_admin'):
        flash("Accès refusé.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        image_file = request.files['image_file']
        texte = request.form['texte']  # récupérer le texte
        filename = image_file.filename
        image_file.save(os.path.join('static/images', filename))

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO apropos (image, texte) VALUES (?,?)", (filename, texte))
        conn.commit()
        conn.close()
        flash("Image publiée avec succès")
        return redirect(url_for('admin_apropos'))

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM apropos")
    apropos = c.fetchall()
    conn.close()
    return render_template('admin_apropos.html', apropos=apropos)



@app.route('/apropos')
def apropos():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM apropos")
    apropos_data = c.fetchall()
    conn.close()
    return render_template('apropos.html', apropos=apropos_data)

@app.route('/delete_apropos/<int:apropos_id>')
def delete_apropos(apropos_id):
    if not session.get('is_admin'):
        flash("Accès refusé.")
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM apropos WHERE id=?", (apropos_id,))
    conn.commit()
    conn.close()
    flash("Image supprimée avec succès.")
    return redirect(url_for('admin_apropos'))





if __name__ == '__main__':
    app.run(debug=True)
