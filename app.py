from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy import func
from datetime import datetime

app = Flask(__name__)

ENV = 'MIM'

if ENV == 'dev':
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:HASŁO@localhost/projekt_bazy'
else:
    app.debug = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://jb432938:jb432938jb432938@lkdb/mrbd'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


with app.app_context():
    Base = automap_base()
    Base.prepare(autoload_with = db.engine)
    Uzytkownicy = Base.classes.uzytkownicy
    Wybory = Base.classes.wybory
    Glosy = Base.classes.glosy
    Kandydaci = Base.classes.kandydaci


def zaladuj_panel(czy_komisja, login=None):
    data = datetime.now()
    if czy_komisja:
        ukryte_wyniki = db.session.query(Wybory).filter(Wybory.wyniki_widoczne==False).all()
        do_archiwizacji = db.session.query(Wybory).filter(Wybory.archiwizacja == False, Wybory.glosowanie_do < data).all()
        return render_template('panel_komisja.html', ukryte_wyniki=ukryte_wyniki, do_archiwizacji=do_archiwizacji)
    else:
        aktywne_zgloszenia = db.session.query(Wybory).filter(Wybory.zglaszanie_od <= data, Wybory.zglaszanie_do >= data).all()
        aktywne_wybory = db.session.query(Wybory).filter(Wybory.glosowanie_od <= data, Wybory.glosowanie_do >= data).all()
        dostepne_wyniki = db.session.query(Wybory).filter(Wybory.wyniki_widoczne == True).all()
        kandydaci_lista = []
        for wybory in aktywne_wybory:
            query = db.session.query(Uzytkownicy.imie, Uzytkownicy.nazwisko).join(
                    Kandydaci, Uzytkownicy.id==Kandydaci.id_uzytkownika).filter(
                    Kandydaci.id_wybory==wybory.id)
            kandydaci_lista.append(query.all())
        return render_template('panel_wyborca.html', aktywne_wybory=aktywne_wybory,
                    aktywne_zgloszenia=aktywne_zgloszenia, login=login, 
                    kandydaci_lista=kandydaci_lista, dostepne_wyniki=dostepne_wyniki)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        login = request.form['login']
        haslo = request.form['haslo']

        if db.session.query(Uzytkownicy).filter(
            Uzytkownicy.login == login).count() == 0:
            return render_template('index.html', message="Nie ma cię w bazie użytkowników. Sorry ;c")
        else:
            user = db.session.query(Uzytkownicy).filter(Uzytkownicy.login == login).first()
            if user.haslo != haslo:
                return render_template('index.html', message="Błędne hasło!")
            if user.komisja: # True jesli komisja
                return zaladuj_panel(czy_komisja=True)
            else:
                return zaladuj_panel(czy_komisja=False, login=login)
            

@app.route('/logout', methods=['POST'])
def logout():
    if request.method == 'POST':
        return render_template('index.html')
                

@app.route('/panel', methods=['POST'])
def powrot():
    if request.method == 'POST':
        czy_komisja = int(request.form['powrot'])
        if czy_komisja:
            login = None
        else:
            login = request.form['login']
    return zaladuj_panel(czy_komisja, login)


################ Obsluga PANELU KOMISJI:

@app.route('/dodano_wyborce', methods=['POST'])
def dodaj_wyborce():
    if request.method == 'POST':
        login = request.form['login']
        haslo = request.form['haslo']
        imie = request.form['imie']
        nazwisko = request.form['nazwisko']

        if request.form['rola'] == "Komisja":
            rola = True
        else:
            rola = False
        
        if db.session.query(Uzytkownicy).filter(Uzytkownicy.login == login).count() == 0:
            new_user = Uzytkownicy(login=login, haslo=haslo, imie=imie, nazwisko=nazwisko, komisja=rola)
            db.session.add(new_user)
            db.session.commit()
            return render_template('panel_sukces.html', message="Dodano nowego wyborcę :D", powrot_komisja=True)
        else:
            return render_template("panel_sukces.html", message="Wyborca już jest w bazie!", powrot_komisja=True)


@app.route('/dodano_wybory', methods=['POST'])
def dodaj_wybory():
    if request.method == 'POST':
        tytul = request.form['tytul']
        zgl_od = request.form['zgl_od']
        zgl_do = request.form['zgl_do']
        glo_od = request.form['glo_od']
        glo_do = request.form['glo_do']
        archiwizacja = False

        if request.form['wyniki'] == 'Widoczne':
            wyniki = True
        else:
            wyniki = False
        
        nowe_wybory = Wybory(tytul=tytul, archiwizacja=archiwizacja, zglaszanie_od=zgl_od, zglaszanie_do=zgl_do, glosowanie_od=glo_od, glosowanie_do=glo_do, wyniki_widoczne=wyniki)
        db.session.add(nowe_wybory)
        db.session.commit()
        return render_template('panel_sukces.html', message="Dodano nowe wybory :D", powrot_komisja=True)


@app.route('/ujawniono_wyniki', methods=['GET', 'POST'])
def upublicznij():
    if request.method == 'POST':
        tablica = request.form.getlist('tablica')
        if len(tablica) == 0:
            return render_template('panel_sukces.html', message="Proszę zaznaczyć wyniki do upublicznienia!", powrot_komisja=True)
        for id in tablica:
            record = db.session.query(Wybory).filter(Wybory.id == int(id)).first()
            record.wyniki_widoczne = True
            db.session.commit()
    return render_template('panel_sukces.html', message="Upubliczniono wyniki wyborów!", powrot_komisja=True)


@app.route('/zarchiwizowano_wybory', methods=['GET', 'POST'])
def archiwizuj():
    if request.method == 'POST':
        tablica = request.form.getlist('tablica')
        if len(tablica) == 0:
            return render_template('panel_sukces.html', message="Proszę zaznaczyć wybory do zarchiwizowania!", powrot_komisja=True)
        for id in tablica:
            record = db.session.query(Wybory).filter(Wybory.id == int(id)).first()
            record.archiwizacja = True
            db.session.commit()
    return render_template('panel_sukces.html', message="Zarchiwizowano wybory!", powrot_komisja=True)


########## Obsluga PANELU WYBORCY

@app.route('/dodaj_kandydata', methods=['POST'])
def dodaj_kandydata():
    if request.method == 'POST':
        imie = request.form['imie']
        nazwisko = request.form['nazwisko']
        id_wybory = request.form['id_wybory']
        login = request.form['login']

        # weryfikacja czy osoba istnieje w bazie danych uzytkownikow:
        uzytkownik = db.session.query(Uzytkownicy.id).filter(Uzytkownicy.imie==imie, Uzytkownicy.nazwisko==nazwisko, Uzytkownicy.komisja==False)
        if uzytkownik.count() == 1:
            # Szukam czy jest już kandydatem w rzeczonych wyborach:
            query = db.session.query(Kandydaci.id_wybory, Uzytkownicy.id, Uzytkownicy.imie, Uzytkownicy.nazwisko).join(
                    Uzytkownicy, Uzytkownicy.id==Kandydaci.id_uzytkownika).filter(
                    Uzytkownicy.imie==imie, Uzytkownicy.nazwisko==nazwisko, Kandydaci.id_wybory==id_wybory)
            
            if query.count()==0:
                id_uzytkownika = db.session.query(Uzytkownicy.id).filter(Uzytkownicy.imie==imie, Uzytkownicy.nazwisko==nazwisko)
                nowy_kandydat = Kandydaci(id_uzytkownika=id_uzytkownika, id_wybory=id_wybory)
                db.session.add(nowy_kandydat)
                db.session.commit()
                return render_template('panel_sukces.html', message="Dodano nowego kandydata :D", powrot_komisja=False, login=login)
            else:
                return render_template("panel_sukces.html", message="Kandydat został już zgłoszony do tych wyborów!", powrot_komisja=False, login=login)
  
        elif uzytkownik.count() == 0:
            return render_template("panel_sukces.html", message="Nie ma wyborcy w bazie!", powrot_komisja=False, login=login)

        elif uzytkownik.count() > 1:
            return render_template("panel_sukces.html", message="Istnieje więcej niż jeden użytkowników o podanym imieniu i nazwisku!",
                            powrot_komisja=False, login=login)


@app.route('/oddaj_glos', methods=['POST'])
def oddaj_glos():
    if request.method == 'POST':
        login = request.form['login']
        imie = request.form['imie']
        nazwisko = request.form['nazwisko']
        id_wybory = request.form['id_wybory']
        id_uzytkownika = db.session.query(Uzytkownicy.id).filter(Uzytkownicy.login==login).first()

        # weryfikacja czy wyborca glosowal juz w tych wyborach:
        wyborca = db.session.query(Glosy.id).join(Uzytkownicy, Uzytkownicy.id==Glosy.id_uzytkownika).filter(
            Uzytkownicy.login==login, Glosy.id_wybory==id_wybory)
        
        if wyborca.count()==0: # nie glosowal, wiec moze zaglosowac
            # Sprawdzam czy wybrany kandydat faktycznie kandyduje w rzeczonych wyborach:
            query = db.session.query(Kandydaci.id).join(
            Uzytkownicy, Uzytkownicy.id==Kandydaci.id_uzytkownika).filter(
                Uzytkownicy.imie==imie, Uzytkownicy.nazwisko==nazwisko, Kandydaci.id_wybory==id_wybory)
            
            if query.count()==0: # nie kandyduje
                return render_template('panel_sukces.html', message="Rzeczony kandydat nie kandyduje w tych wyborach!",
                                       powrot_komisja=False, login=login)
            
            elif query.count()==1: # kandyduje
                id_kandydat = query.first()
                nowy_glos = Glosy(id_uzytkownika=id_uzytkownika[0], id_wybory=id_wybory, id_kandydat=id_kandydat[0])
                db.session.add(nowy_glos)
                db.session.commit()
                return render_template("panel_sukces.html", message="Oddano głos!",
                                       powrot_komisja=False, login=login)
  
        elif wyborca.count() > 0:
            print("Wyborca glosowal juz w tych wyborach!!")
            return render_template("panel_sukces.html", message="Już zaglosowaleś w tych wyborach!",
                                   powrot_komisja=False, login=login)


@app.route('/zobacz_wyniki', methods=['POST'])
def zobacz_wyniki():
    if request.method == 'POST':
        id_wybory = request.form['id_wybory']
        tytul_wybory = db.session.query(Wybory.tytul).filter(Wybory.id==id_wybory).first()
        login = request.form['login']
        wyniki = db.session.query(Glosy.id_kandydat, Uzytkownicy.imie, 
                                  Uzytkownicy.nazwisko, func.count()).join(
                                      Kandydaci, Kandydaci.id == Glosy.id_kandydat
                                  ).join(
                                      Uzytkownicy, Uzytkownicy.id == Kandydaci.id_uzytkownika
                                  ).filter(Glosy.id_wybory == id_wybory).group_by(
                                      Glosy.id_kandydat, Uzytkownicy.imie, Uzytkownicy.nazwisko
                                  ).order_by(func.count().desc()).all()

        return render_template('panel_wyniki.html', wyniki=wyniki, tytul_wybory=tytul_wybory,
                               powrot_komisja=False, login=login)


if __name__ == '__main__':
    app.debug = True
    app.run()