from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from .forms import PostForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib.auth.models import User
from pymongo import MongoClient
import datetime
from django.contrib import messages


@login_required(login_url='login')
# fai vedere tutti i post in ordine cronologico(da quello più vecchio a quello più recente)
def post_list(request):
    posts = Post.objects.filter().order_by('datetime')
    return render(request, 'transaction/post_list.html', {'posts': posts})


@login_required(login_url='login')
#vedi il post singolo
def post_detail(request, pk=None):
    post = get_object_or_404(Post)
    return render(request, 'post_detail.html', {'post': post})


@login_required(login_url='login')
def post_new(request):
    # prendo l'email inserita
    id = request.user.id
    # prendo l'email corrispondente all'utente che scrive
    my_mail = request.user.email
    # prendo l'ordine inserito
    if request.method == "POST":
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.datetime = timezone.now()
            # invoco la funzione permission_request per controllore se l'email inserita garantisce qualche autorizzazione o meno
            permission = permission_request(post.permission_user, id, my_mail)
            # se l'email inserita è sbagliata o non è stata inserita nessuna autorizzazione
            if permission == 'Deny':
                messages.info(request, 'ATTENTION! YOU HAVE NO AUTHORIZATION FROM THIS EMAIL')
                return render(request, 'transaction/post_edit.html', {'form': form})
            # invoco la funzione transaction per registrare, o meno, le informazioni appena inserite
            result = transaction(post.price_per_unit, post.type_of_transaction, post.user_id, post.amount, post.content, post.permission_user, permission)
            # se si ha il permesso di scrivere solo i post e si commette un errore...
            if result == -3:
                messages.info(request, 'ATTENTION! ACCORDING TO YOU PERMISSION YOU CAN ONLY WRITE A POST')
                return render(request, 'transaction/post_edit.html', {'form': form})
            # se all'email inserita, non corrisponde nessuna autorizzazione...
            if result == -2:
                messages.info(request, 'ATTENTION! YOU DO NOT HAVE THE PERMISSION TO WRITE A POST')
                return render(request, 'transaction/post_edit.html', {'form': form})
            # se l'ordine è uguale a un altro già inserito (dallo stesso utente), l'ordine non viene salvato
            if result == -1:
                messages.info(request, 'ATTENTION! YOU HAVE ALREADY PLACE THIS ORDER')
                return render(request, 'transaction/post_edit.html', {'form': form})
            # se il prezzo e il tipo di ordine sono uguali, ma la quantità è differente, allora l'ordine viene modificato
            if result == 0:
                messages.info(request, 'GREAT! YOU CHANGE YOUR ORDER!')
                return render(request, 'authentication/base.html')
            # se l'operazione è andata a buon fine salva l'ordine
            if result == 1:
                post.save()
            # se l'ordine inserito è stato completamente eseguito
            if result == 2:
                messages.info(request, 'GREAT! YOUR ORDER HAS BEEN EXECUTED!!! CHECK YOUR BALANCE')
                return render(request, 'authentication/base.html')
            # se l'utente sbaglia a inserire l'ordine...
            if result == 4:
                messages.info(request, 'SOMETHING IS WRONG!!!')
                return render(request, 'transaction/post_edit.html', {'form': form})
            # se l'utente non ha fondi, allora l'ordine non viene inserito
            if result == 5:
                messages.info(request, 'ATTENTION! YOU DO NOT HAVE ENOUGH FUNDS!!')
                return render(request, 'transaction/post_edit.html', {'form': form})
            return redirect('post_detail')

    else:
        form = PostForm()
    return render(request, 'transaction/post_edit.html', {'form': form})


@login_required(login_url='login')
# modifica il post
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.user == post.user:
        if request.method == "POST":
            form = PostForm(request.POST, instance=post)
            if form.is_valid():
                post = form.save(commit=False)
                post.user = request.user
                post.datetime = timezone.now()
                post.save()
                return redirect('post_detail', pk=post.pk)
        else:
            form = PostForm(instance=post)
        return render(request, 'api/post_edit.html', {'form': form})
    else:
        return render(request,'api/post_detail.html', {'post': post})


# la funzione trasaction riceve dalla funzione post_news 7 variabili e controlla se deve salvare o meno il post.
# Inoltre scorre il database e controlla se l'ordine inserito nel post, incotra un ordine di 'segno opposto'. In tale caso avverrà una transazione
def transaction(price_per_unit, type_of_transaction, user, amount,  content, email_permission, permission):
    # contolla se ci sono errori di inserimento
    first= check_transaction(price_per_unit, type_of_transaction, amount, content, permission)
    if first != 0:
        return first
    # controllo che il post inserito da tastiera non si già esistente
    double = trova_double(price_per_unit, email_permission, type_of_transaction, user,  amount, content)
    if double != 1:
        return double
    # richiamo il database
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['transaction_post']
    # controllo il tipo di transazione inserita dall'utente e creo una variabile di 'segno opposto'
    if type_of_transaction == 'BUY':
        buy_sell = 'SELL'
    if type_of_transaction == 'SELL':
        # controllo se l'utente corrispondente all'email inserita ha realmenti la quantità di BTC che vuole vendere
        check_balance = check_funds(email_permission, amount)
        if check_balance != 0:
            # se l'user non possiede i BTC allora il post non viene inserito
            return check_balance
        buy_sell = 'BUY'
    # se ho inserito un ordine compilando solo la sezione 'content'
    if type_of_transaction == None:
        return 1
    # se il database è vuoto lo popolo
    if len(Post.objects.values()) == 0:
        return 1
    lista_vett = []
    # creo un cursore
    lista = collection.find({'amount': amount})
    # lo metto in una lista
    for list in lista:
        lista_vett.append(list)
    # se la lista è vuota pubblico il post
    number_of_order = len(lista_vett)
    if number_of_order == 0:
        return 1
    # scorro la lista
    for list in lista_vett:
        # estraggo le informazioni che mi servono
        quant = list.get('amount')
        usertr = list.get('user_id')
        permission_post = list.get('permission_user')
        type_of_tran = list.get('type_of_transaction')
        _id = list.get('_id')
        price = list.get('price_per_unit')
        # se la quantità trovata, è maggiore di quella passata nella funzione transaction
        if float(quant) == float(amount):
            # controllo se i destinatari della transazione (cioè coloro che posseggono le email insetite), sono diversi
            if str(find_user(email_permission)) != str(find_user(permission_post)):
                # controllo che i due post abbiano tipi di transazioni differenti
                if type_of_tran != type_of_transaction:
                    # controllo che non ci siano dipendenze tra i soggetti destinatari della transazione
                    if find_tangle(user, email_permission, usertr, permission_post) == 1:
                        # se la quantità trovata, è maggiore di quella passata nella funzione transaction
                        if float(quant) == float(amount) and str(user) != str(usertr):
                            # controllo che il prezzo passato alla funzione transaction sia maggiore o uguale al prezzo trovato
                            # e il tipo di transazione dell'altro ordine è SELL
                            if float(price_per_unit) >= float(price) and type_of_tran == 'SELL':
                                final = float(quant)
                                # registro l'ordine
                                order(user, price_per_unit, final, type_of_transaction, usertr, buy_sell, email_permission,
                                      permission_post)
                                # cancello il post che ho incontrato
                                collection.remove({'_id': _id})
                                # aggiungo alla lista dei risultati 2
                                return 2
                            #-----------------VARINTE CHE HO AGGIUNTO NON RICHIESTA------------------#
                            # se il tipo di transazione dell'altro ordine è BUY e i prezzi sono uguali
                            if float(price_per_unit) == float(price) and type_of_tran == 'BUY':
                                final = float(quant)
                                # registro l'ordine
                                order(user, price_per_unit, final, type_of_transaction, usertr, buy_sell, email_permission,
                                      permission_post)
                                # cancello il post che ho incontrato
                                collection.remove({'_id': _id})
                                # aggiungo alla lista dei risultati 2
                                return 2
                            #-----------------------------------------------------------------------#
    # in tutti gli altri caso salvo il post
    return 1


# la funzione trova_double cerca se l'utente ha già inserito il post
def trova_double(price, email, buy_sell, user,  amount, content):
    lista_vettore = []
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['transaction_post']
    # creo un cursore con l'id dell'utente
    lista_find_price = collection.find({'user_id': user})
    # scorro il cursore
    for lista in lista_find_price:
        lista_vettore.append(lista)
    # se l'utente non ha mia scritto un post
    if len(lista_vettore) == 0:
        return 1
    #scorro il vettore
    for lista in lista_vettore:
        # prendo le informazioni di cui ho bisongo
        type_of_transaction = lista.get('type_of_transaction')
        permission_email= lista.get('permission_user')
        _idpost = lista.get('_id')
        quanti_post = lista.get('amount')
        price_other = lista.get('price_per_unit')
        # se l'user ha pubblicato un post con il prezzo passato alla funzione find_double
        if float(price) == float(price_other):
            # se l'user ha pubblicato un post con lo stesso tipo di transazione, e la stassa permission_email
            if str(type_of_transaction) == str(buy_sell) and str(permission_email) == str(email):
                # se la quantità è la stessa
                if str(amount) == str(quanti_post):
                    # il post è doppio
                    return -1
                # se la quantità è differente
                if str(amount) != str(quanti_post):
                    # faccio l'update del post
                    update_post(user, email, amount, price, buy_sell, content, _idpost)
                    return 0
    # in tutti gli altri casi non ci sono doppioni
    return 1


# la funzione update post aggiorna il documento corrispondente all'_id assegnato
def update_post(usertr, permission_post, resto, price, type_of_tran, content, _id):
    # richiamo il database
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['transaction_post']
    post = {
        'user_id': usertr,
        'permission_user': permission_post,
        'amount': resto,
        'price_per_unit': price,
        'crypto': 'BTC',
        'type_of_transaction': type_of_tran,
        'content': content,
        'datetime': datetime.datetime.now(),
    }
    collection.update({'_id': _id}, post)


# la funzione find_tangle controllo che non ci siano dipendenza tra i soggetti destinatari della transazione.
# se ci sono dipendeze la transazione non va avanti
def find_tangle(user_a, email_post_a, user_b, email_post_b):
    lista_subs = []
    if user_a == find_user(email_post_a) and user_b == find_user(email_post_b):
        return 1
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['app_profile']
    # controllo che il destinatario non abbia nessuna relazione con i soggetti dell'altro ordine incontrato (l'user e
    # il destinatario della transazione)
    check= [find_user(email_post_a), find_email(user_b), email_post_b]
    print(check)
    i = 1
    #controllo che tra l'emai_a e user_b e email_post_b non ci siano dipendenze
    lista = collection.find({'user_id': check[0]})
    for lis in lista:
        lista_subs.append(lis)
    for email in lista_subs:
        for split in email.get('subprofile'):
            if str(check[i]) in str(split):
                #se ci sono dipendenze la transazione non va avanti
                return 0
        if i == 2:
            break
        i += 1
    # se non ci sono dipendeze allora la transazione va avanti
    return 1


#la funzione find_email recupera dall' used_id l'email corrispondente
def find_email(user):
    lista_mail = []
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['app_profile']
    lista = collection.find({'user_id':user})
    for lis in lista:
        lista_mail.append(lis)
    for find in lista_mail:
        for split in find.get('ips'):
            return split.get('email')


# la funzione chceck_transaction controlla se ci sono errori nell'inserimento dell'ordine
def check_transaction( price, type_of_transaction, amount, content, permission):
    if price == None:
        price = 0.0
    if amount == None:
        amount = 0.0
    # se l'utente ha inserito amount o prezzo negativo il post non viene considerato
    if amount < 0 or price < 0:
        return 4
    # se l'utente ha il permesso solo di inserire i post
    if permission == 'post message':
        if len(content) == 0:
            return -3
        if amount > 0 or price > 0:
            return -3
        if type_of_transaction != None:
            return -3
    # se l'utente non ha il permesso di usare la sezione content
    if permission == 'place orders':
        if len(content) != 0:
            return -2
    # se l'utente inserisce un post vuoto, il post non viene considerato
    if len(content) == 0:
        if amount == 0.0 and price == 0.0:
            if type_of_transaction == None or type_of_transaction != None:
                return 4
    # se l'utente sbaglia a inserire l'ordine, l'ordine non viene considerato
    if type_of_transaction == None:
        if price != 0.00 or amount != 0.00:
            return 4
    else:
        if price == 0.00 or amount == 0.00:
            return 4
    return 0


# la funzione check_fund controlla che i BTC inseriti nell'ordine di vendita, siano veramente nelle disponibilità dell'user
def check_funds(email_permission,amount):
    sell = 0.00
    lista_wallet = []
    lista_order = []
    user = find_user(email_permission)
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['authentication_btcwallet']
    # recupero i BTC regitrati nel wallet
    a=collection.aggregate([{'$match': {'user_id': user}}, {'$group': {'_id': '$user_id', 'total': {'$sum': '$wallet'}}}])
    for wallet in a:
        lista_wallet.append(wallet)
    for i in lista_wallet:
        # prendo i BTC totali posseduti dall'utente
        total = (i.get('total'))
    # recupero i BTC derivanti dai post con type_of_transaction == SELL
    collection = db['transaction_post']
    b = collection.find({'permission_user': email_permission})
    for order in b:
        lista_order.append(order)
    for i in lista_order:
        if str(i.get('type_of_transaction')) == 'SELL':
            sell += float(i.get('amount'))
    # sottraggo ai BTC che possiede l'utente, i BTC derivanti dalla vendita nei post, e i BTC passati alla funzione check_funds
    final_sell = float(total) - float(sell) - float(amount)
    # se la quantità di BTC dell'operazione precedente è negativa il post non viene inserito
    if final_sell < 0:
        return 5
   # l'user possiede i BTC
    return 0


# la funzione find_user prende l'email inserita in input e trova l'user_id corrispondente
def find_user(email):
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['app_profile']
    lista = collection.find()
    for find in lista:
        a=str(find).split('subprofile')
        if str(email) in str(a[:-1]):
            return find.get('user_id')


# la funzione order registra la transazione nel profilo dei due utenti e invoca la funzione update_wallet per aggiorna i wallets
# (ipotizzo che non ci siano limiti di moeta fiat)
def order(user, price, final, type_of_transaction, usertr, buy_sell, email_permission, permission_post):
    # recupero l'user_id dei due utenti
    user_account =find_user(email_permission)
    usert_account =find_user(permission_post)
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['app_order']

    post1 = {
        'profile': user,
        'buy_sell':type_of_transaction,
        'user_account': user_account,
        'price_per_unit': price,
        'amount': final,
        'updated': datetime.datetime.now()
    }
    # ordine dell'utente che ha inserito l'ultimo post
    collection.insert(post1)

    post2 = {
        'profile': usertr,
        'buy_sell': buy_sell,
        'user_account': usert_account,
        'price_per_unit': price,
        'amount': final,
        'updated': datetime.datetime.now()
    }
    # ordine dell'untete dell'altro post
    collection.insert(post2)
    # aggiorna i waller degli utenti
    update_wallet(final, type_of_transaction, user_account, price, permission_post)


# la funzione upadate_wallet aggiorna i wallets dei due utenti andando a registre in autentication_btcwallet tutte le
# transazioni
def update_wallet(final, type_of_transaction, user_account, price, permission_post):
    # recupero l'user_id dell'atro utente
    usertr = find_user(permission_post)
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['authentication_btcwallet']
    # trovo l'user_id corrispondente all'email inserita
    # stabilisco i BTC da aggiungere o sottrarre al wallet degli utenti
    if type_of_transaction == 'BUY':
        # acquista user_account, vende permission_post
        buy_user = user_account
        sell_user = usertr
    else:
        # permission_post acquista, user_account vende
        sell_user = user_account
        buy_user = usertr

    post_buy = {
        'user_id': buy_user,
        'wallet': final,
        'unit_price': price,
        'crypto': 'BTC',
        'updated': datetime.datetime.now()
    }
    # aggiornamento per il compratore
    collection.insert(post_buy)

    post_sell = {
        'user_id': sell_user,
        'wallet': -final,
        'unit_price': price,
        'crypto': 'BTC',
        'updated': datetime.datetime.now()
    }
    # aggiornamento per il veditore
    collection.insert(post_sell)


# la funzione permission_request prende da imput l'email con la quale si vuole effettuare l'ordine
def permission_request(email, id, my_mail):
    # invoca la funzione mongodb_search per verificare l'email inserita dall'utente
    response= mongodb_search(email, id, my_mail)
    return response


# la funzione mongobd_search controlla se l'email inserita ha garantito un permesso all'utente. In alternativa gli
# restituisce un errore
def mongodb_search(email, id, my_mail):
    lista_mongo = []
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['app_profile']
    # creo un cursore in mongodb per trovare l'email dell'utente contenuta in ips
    mongo=collection.find({'ips.email':email})
    for list in mongo:
        lista_mongo.append(list)
    # creo una 'lista' prendendo le informazioni del prfilo degli utenti (non uso mongodb direttamente)
    user_mail = User.objects.values()
    # per ogni utente vado a scorrere la 'lista'
    for row in user_mail:
        # se trova che la mail inserita dall'utente corrisponde alla email dell'utente stesso
        if str(email) == row.get('email') and str(id) == str(row.get('id')):
            return 'self'
    # scorro la lista lista_mongo, per cercare se nella sezione subprofile dell'utente corrispondente alla email inserita, esiste l'email dell'utente che scrive...
    # e il tipo di permesso concesso
    for subprofile in lista_mongo:
        for elem in subprofile.get('subprofile'):
            if str(my_mail) == str(elem.get('email')) and 'place orders' == str(elem.get('permission')):
                return 'place orders'
            if str(my_mail) == str(elem.get('email')) and 'all' == str(elem.get('permission')):
                return 'all'
            if str(my_mail) == str(elem.get('email')) and 'post messages' == str(elem.get('permission')):
                return 'post message'
    # se non ci sono permessi concessi restitusce Deny
    return 'Deny'
