import datetime

from bson.objectid import ObjectId
from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from pymongo import MongoClient
from transaction.models import Post
from transaction.views import find_user

from .forms import *
from .models import *


# la funzione accountSetting scrive e prende le informazione da Userpage
def accountSettings(request):
    customer = request.user.id
    obj = find_idobj(customer)
    form = UserpageForm()
    if request.method == 'POST':
        form = UserpageForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            write_account(obj, customer, post.name, post.phone, post.email)#, post.profile_pic)
    context = {'form': form}
    return render(request, 'app/account_setting.html', context)


# la funzione find_odobj prende l'user_id e recupera l'_id del documento
def find_idobj(customer):
    obj = 0
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['app_userpage']
    user = collection.find({'user_id': customer})
    for u in user:
        objnew = u.get('_id')
        return objnew
    if obj == 0:
        return obj

# la funzione write_account prende le informazioni inserite da tastiera e le scrive/sovrascrive in un documento in Userpage
def write_account(obj, user_id , name= "...", phone= "...", email="..."):#, photo):
    # richiamo il database
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['app_userpage']
    post = {
        'user_id': user_id,
        'name': name,
        'phone': phone,
        'email': email,
        'date_created': datetime.datetime.now()
        #'profile_pic': photo,
    }
    if obj == 0:
        collection.insert(post)
    else:
        collection.update({'_id': obj}, {'$set': post})


# la funzione account_user restituisce le informazioni dell'utente riprese da Userpage
def account_user(request):
    user = request.user.id
    email = request.user.email
    # richiedo le informazioni corrispondenti all'utente
    account_list = Userpage.objects.values()
    accounts = []
    listn = []
    # se è la prima volta che uso il database, lo popolo
    if len(account_list) == 0:
        accounts.append(write_account(find_idobj(user), user))
    # altrimenti prendo le informazioni corrispondenti a user, o ne creo di nuove
    else:
        for account in account_list:
            if str(user) in str(account.get('user_id')):
                accounts.append(account)
    if len(accounts) == 0:
        accounts.append(write_account(find_idobj(user),user))
    # recupero i permessi concessi da user
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['app_profile']
    #richiedo da mongodb le informazioni dell'user_id, contenute in permission
    lista = collection.find({'user_id': user})
    for list in lista:
        listn.append(list)
    # della sezione profile prendo la lista dei subprofile
    for lis in listn:
        a=lis.get('subprofile')
    #se subprofile è vuota, lo faccio sapere
    if len(a) == 0:
        none = {'any': 'You have not given any permission'}
        listn.append(none)
    # la funzione find_post_user mi restituisce i posts scritti dall'utente
    posts = len(find_post_user(user))
    # raccolgo i posts scritti dagli utenti a cui l'user ha dato il permesso, e che hanno nel campo permission_user, l'email dell'utente
    others = len(find_post_other(email, user))
    # recupero i BTC associati all'utente
    btc = btc_user(user)
    # tutte le informazioni  che ho raccolto le metto in un dizionario di nome 'data' e le restituisco alla pagina html
    data = {
        'accounts': accounts,
        'lista': listn,
        'posts': posts,
        'others': others,
        'btcs': btc
    }
    return render(request, 'app/account.html', {'data': data})


# la funzione find_post_user recupera i post scritti da user
def find_post_user(user):
    list_post = []
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    # qui va il nome del database (nel mio caso 'transaction_post')
    collection = db['transaction_post']
    post=collection.find({'user_id': user})
    for pos in post:
        list_post.append(pos)
    return list_post


# la funzione find_post_other recupera i post deggli utenti che hanno avuto il permesso da user e che hanno nella sezione
# account la variabile email passata alla funzione
def find_post_other(email, user):
    other_list = []
    return_list = []
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['transaction_post']
    posts = collection.find({'account': email})
    for post in posts:
        other_list.append(post)
    for other in other_list:
        if str(other.get('user_id')) != str(user):
            return_list.append(other)
    return return_list


# la funzione account_list restituisce alla pagine html i post associati all'utente con il relativo _id
def account_list(request):
    code_list= []
    user = request.user.id
    lista = find_post_user(user)
    i = 0
    for id in lista:
        post = {
            'posts': Post.objects.filter(user_id=user).order_by('-datetime')[i],
            'id': id.get('_id')
        }
        code_list.append(post)
        i += 1
    return render(request, 'app/account_post.html', {'code': code_list})


# la funzione account_other restituisce alla pagine html i post degli utenti che hanno ricevuto il permesso da user,
# e nella sezione account hanno inserito la variabile email (che corrisponde all'email di user)
def account_other(request):
    code_list = []
    user = request.user.id
    email = request.user.email
    lista = find_post_other(email, user)
    i = 0
    for id in lista:
        post = {
            'posts': Post.objects.filter(user_id=user).order_by('-datetime')[i],
            'id': id.get('_id')
        }
        code_list.append(post)
        i += 1
    return render(request, 'app/account_other.html', {'code': code_list})


# recupera i BTC dell' user
def btc_user(user):
    # richiamo il database
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['authentication_btcwallet']
    # recupero i BTC regitrati nel wallet
    btc = collection.aggregate(
        [{'$match': {'user_id': user}}, {'$group': {'_id': '$user_id', 'total': {'$sum': '$wallet'}}}])
    for b in btc:
        balance = b.get('total')
    return balance


# la funzione check_transactions recupera il saldo il EUR, il saldo in BTC e la lista delle transazioni registrate in wallet
# e le restrituisce in html
def check_transactions(request):
    id = request.user.id
    saldo = 0
    lista_user = []
    list_user = wallet(id)
    for user in lista_user:
        if user.get('wallet') > 0:
            saldo -= user.get('unit_price')
        else:
            saldo += user.get('unit_price')
    data = {
        'btcs': btc_user(id),
        'transactions': list_user,
        'balance': saldo
    }
    return render(request, 'app/account_transactions.html', {'data': data})


# la funzione wallet recupara la lista delle transazioni dell'utente registrate in wallet
def wallet(user):
    lista_user = []
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['authentication_btcwallet']
    user_curs = collection.find({'user_id': user})
    for user in user_curs:
        lista_user.append(user)
    return lista_user


# la funzione statistics restituisce delle informazioni riguardanti le transazioni dell'utente e le restitusce in html
def statistics(request):
    id = request.user.id
    mean = []
    price_tot = 0
    price_buy = 0
    price_sell= 0
    btc_buy = 0
    btc_sell = 0
    # recupero la lista dei btc registrati in wallet
    list_user = wallet(id)
    # recupero i BTC acquistati/venduti il prezzo per ogni transazione e il costo di un BTC per transazione
    for user in list_user:
        if user.get('wallet') > 0 and user.get('unit_price') > 0:
            btc_buy += user.get('wallet')
            price_buy -= user.get('unit_price')
            unit_price = (user.get('unit_price')/user.get('wallet'))
            mean.append(unit_price)
        else:
            if user.get('unit_price') > 0:
                btc_sell += user.get('wallet')
                price_sell += user.get('unit_price')
                unit_price = -(user.get('unit_price') / user.get('wallet'))
                mean.append(unit_price)
    total_eur = price_buy + price_sell
    for unit in mean:
       price_tot += unit
    if len(mean) == 0:
        tot_mean = 0
    else:
        tot_mean = (price_tot/len(mean))
    data = {
        'btcbuy': btc_buy,
        'btcsell': -btc_sell,
        'pricebuy': -price_buy,
        'pricesell': price_sell,
        'ntransactions': len(mean),
        'totaleur': total_eur,
        'totalbtc': btc_user(id),
        'totmean': tot_mean
    }
    return render(request, 'app/account_statistics.html', {'data': data})


def account(request):
    return render(request, 'app/account_base.html')


# la funzione permissionPage registra i permessi inseriti da tastiera
def permissionPage(request):
    id = request.user.id
    formset = PermissionForm()
    context = {'form': formset}
    if request.method == 'POST':
        formset = PermissionForm(request.POST)
        # prende la mail inserita
        email = request.POST.get('email')
        # prende il tipo di permesso selezionato e la quantità
        permission = request.POST.get('permission')
        if formset.is_valid():
            # se è stata inserito il carettere @ e la funzione mongodb restituisce 1
            if '@' in email:
                response = mongodb(request, id, email, permission)
                if response == 1:
                    #il form viene salvato e si torna alla home
                    formset.save()
                    return redirect('/')
                if response == -1:
                    messages.info(request, 'ATTENTION! SELECT A PERMISSION OR INSERT AN EMAIL')
                    return render(request, 'app/permission.html', context)
                if response == -2:
                    messages.info(request, 'ATTENTION! THIS EMAIL DOES NOT EXIST!')
                    return render(request, 'app/permission.html', context)
                if response == -3:
                    messages.info(request, 'ATTENTION! THIS IS YOUR EMAIL')
                    return render(request, 'app/permission.html', context)
            else:
                messages.info(request, 'ATTENTION! INSERT A VALID EMAIL!')
                return render(request, 'app/permission.html', context)
    return render(request, 'app/permission.html', context)


# gestisce l'inserimento dei dati nel server MongoDB
def mongodb(request, id, email, permission):
    email_user = request.user.email
    if str(email) == str(email_user):
        return -3
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['app_profile']
    if len(permission) == 0 or len(email) == 0:
        return -1
    email_checked = check_email(email)
    # controllo che l'email inserita corrisponda a un user registrato
    if email_checked == 1:
        # se l'email esiste, creo un cursore per cercare il documento corrispondente all'id
        user = collection.find({'user_id': id})
        # scorro il cursore per controllore se subprofile è vuoto
        for u in user:
            is_first = u.get('subprofile')
        # se è vuoto lo popolo con un array
        if len(is_first) == 0:
            collection.update({'user_id': id}, {'$set': {'subprofile': write_permission_first(email, permission)}},
                              upsert=True)
            messages.info(request, 'GREAT!!! YOU GRANTED YOUR FIRST PERMISSION!')
            return 1
        # se non è vuoto, controllo se l'email sia stata già inserita dall'utente, creando un cursore
        if len(is_first) != 0:
            index = collection.find({'user_id': id}, {'subprofilie': is_first})
            # converto il cursore in stringa per confrontare le stringhe prese con il metodo POST
            for (i) in index:
                dictionary = str(i).split('{')
                for row in dictionary:
                    # se l'email e l'autorizzazione sono già presenti, lo faccio sapere all'utente
                    if email in row and permission in row:
                        messages.info(request, 'ATTENTION!!! PERMISSION ALREADY GRANTED!')
                        return 0
                    # se solo l'email è stata inserita, allora modifico l'autorizzazione e lo faccio sapere all'utente
                    elif email in row and permission not in row:
                        # elimino la vecchia autorizzazione con update, e con la funzione write_permission aggiorno app_profile
                        collection.update({'user_id': id}, {'$pull': {'subprofile': {'email': email}}})
                        write_permission(id, collection, email, permission)
                        # faccio sapere all'utente che ha modificato l'autorizzazione
                        messages.info(request, 'YOU HAVE CHANGED A PERMISSION!')
                        return 1
            # se l'email non esiste aggiungo l'email e il tipo di autorizzazione con la funzione write_permission, e lo faccio sapere all'utente
            write_permission(id, collection, email, permission)
            messages.info(request, 'GREAT!!! YOU GRANTED A PERMISSION!')
            return 1
    # se l'email non esiste lo faccio sapere all'utente
    else:
        return -2


# la funzione check_email controlla che la email inserita corrisponda a un utente registrato
def check_email(email):
    user_mail = User.objects.values('email')
    for mail in user_mail:
        if email in str(mail):
            return 1


# questa funzione serve per popolare per la prima volta il documento con un array e contine l'email e il tipo di autorizzazione concessa
def write_permission_first(email, permission):
    post = {
        "email": email,
        "permission": permission,
        "timestamp": datetime.datetime.now(),
    }
    return [post]


# NOTA LE DUE FUNZIONI (write_permision_first e write_permission) POTREBBERO ESSERE TRANQUILLAMENTE RIASSUNTE IN UNA
# questa funzione serve per popolare l'array e contine l'email e il tipo di autorizzazione concessa
def write_permission(id, collection, email, permission):
    post = {
        "email": email,
        "permission": permission,
        "timestamp": datetime.datetime.now(),
    }
    collection.update({'user_id': id}, {'$push': {'subprofile': post}})


# la funzione deletePermission elimina la concessione selezionata
def deletePermission(request, email):
    id = request.user.id
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['app_profile']
    # con l'id e l'email selezionati elimino il profilo dalla lista con pull
    collection.update({'user_id': id}, {'$pull': {'subprofile': {'email': email}}})
    messages.info(request, 'PERMISSION DELETED')
    # torno alla home
    return redirect('/')


# la funzione deletePosts serve per cancellare un post selezionato dall'utente
def deletePosts(request, id):
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['transaction_post']
    # con l'id rimuovo il post (NOTA: se passo solo id non funziona, devo prima importare ObjectId)
    collection.remove({'_id': ObjectId(id)})
    messages.info(request, 'POST DELETED')
    return redirect('/')
