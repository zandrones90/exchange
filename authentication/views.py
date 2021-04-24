from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .forms import *
from app.models import *
from app.models import Profile
from pymongo import MongoClient
import datetime
from random import random


# la funzione registerPage serve per registrare l'utente
def registerPage(request):
    # se l'user è autenticato, va alla home
    if request.user.is_authenticated:
        return redirect('home')
    # se l'user non è autenticato, fai la registrazione
    else:
        form = CreateUserForm()
        if request.method == "POST":
            form = CreateUserForm(request.POST)
            if form.is_valid():
                utente=form.save()
                #recupero l'id dell'user che si è appena registrato
                user = User.objects.values()[len(User.objects.all())-1]
                id = user.get('id')
                #invoco la funzione drop_btc per registrare i BTC al nuovo utente
                drop_btc(id)
                # una volta salvato vai al login
                return redirect('login')
        context = {'form': form}
        return render(request, 'authentication/register.html', context)


# la funzione loginPage serve per fare il login all'utente
def loginPage(request):
    if request.user.is_authenticated:
        return redirect('home')
    else:
        if request.method == "POST":
            username = request.POST.get('username')
            password = request.POST.get('password')
            # controllo se l'user è nel database
            user = authenticate(request, username=username, password=password)
            # se è nel database faccio fare il login e poi lo mando alla pagina iniziale
            if user is not None:
                login(request, user)
                # richiedo l'username, password e ip dell'utente
                id = request.user.id
                email = request.user.email
                ip = get_client_ip(request)
                # con la funzione mongodb interagisco con il server
                mongodb(id,email,ip)
                # login terminato vado alla HOME
                return redirect('home')
            else:
                # se ha sbagliato il login o l'utente non esiste, mando un messaggio
                messages.info(request, 'username or password is incorrect')
        context = {}

        return render(request, 'authentication/login.html', context)


# logout utente
def logoutUser(request):
    logout(request)
    return redirect('home')


# home
def home(request):
    return render(request, 'authentication/base.html')


# mongodb controlla che l'utente sia già registrato, ed eventualmento crea un nuovo profilo
def mongodb(id, email, ip):
    lista_profile = []
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['app_profile']
    # find serve per controllare se l'utente è registrato o meno: se a fine funzione è = 0 crea un utente
    find = 0
    # se Profile è vuoto (prima volta che uso il sito)
    if len(Profile.objects.values()) == 0:
        # popolo Profile con la funzione insert_first
        collection.insert(insert_first(id, email, ip))
    else:
        # controllo se l'utente sia già registrato:
        if find_user(collection,id) == 'ok':
            # creco di prendere l'_id corrisponde al'utente
            _id_cursor=collection.find({'user_id':id})
            for id in _id_cursor:
                lista_profile.append(id)
            for _id in lista_profile:
                _idobj=_id.get('_id')
            # cerco se l'utene ha  campbiato ip
            change_ip(lista_profile, _idobj, email, ip)
            # se l'utente è già registrato in Profile, si aggiornata l'ora di login
            collection.update({'_id': _idobj}, {"$set": {"timestamp": datetime.datetime.now()}})
            find = 1
        # altrimenti si effettua la registrazione in profile
        if find == 0:
                collection.insert(insert_first(id, email, ip))


# funzione per trovare gli ip degli utenti
def get_client_ip(request):
    try:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
    except:
        ip = ""
    return ip


# la funzione find_user cerca se l'utente corrispondente a id è già inserito in un documento
def find_user(collection, id):
    id_user=collection.find({'user_id': id})
    for i in id_user:
        if (i.get('user_id')) == id:
            return 'ok'
    else:
        return None


# se l'utente non è inserito nel documento, la funzione insert_first crea il profilo dell'utente in mongodb
def insert_first(id, email, ip):
    post = {
        "user_id": id,
        "timestamp": datetime.datetime.now(),
        "ips": [{"email": email,
                "user_ip": ip,
                "timestamp_id": datetime.datetime.now()}],
        'subprofile': {},
    }
    return post


# se l'utente change ip di ingresso, la funzione change_ip aggiorna il profilo dell'utente
def change_ip(collection, id, email, ip):
    # dalla lsita collection estraggo la sezione ips
    for coll in collection:
        ipsn = coll.get('ips')
        # dalla sezione ips estraggo l'ip dell'utente
        for ips in ipsn:
            ips = ips.get('user_ip')
    # se il nuovo ip è differente da quello vecchio, allora si aggiunge alla lista il nuovo ip
    if str(ip) != str(ips):
        mongo = MongoClient(port=27017)
        # qui va il nome del database (nel mio caso 'engine')
        db = mongo['engine']
        collection = db['app_profile']

        post = {"email": email,
                "user_ip": ip,
                "timestamp_id": datetime.datetime.now()
            }
        collection.update({'_id': id}, {'$push': {'ips': post}})


# la funzione drop_btc, a cui passo l'id di un nuovo utente, assegna dei btc 'random' da 0 a max 10
def drop_btc(id):
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection_drop = db['authentication_btcwallet']
    post={
        'user_id': id,
        'wallet': random()*10,
        'price': 0.00,
        'updated': datetime.datetime.now()
    }
    collection_drop.insert(post)


