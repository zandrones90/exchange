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
            permission = permission_request(post.account, id, my_mail)
            # se l'email inserita è sbagliata o non è stata inserita nessuna autorizzazione
            if permission == 'Deny':
                messages.info(request, 'ATTENTION! YOU HAVE NO AUTHORIZATION FROM THIS EMAIL')
                return render(request, 'transaction/post_edit.html', {'form': form})
            # invoco la funzione transaction per registrare, o meno, le informazioni appena inserite
            result = transaction(post.price, post.type_of_transaction, post.user_id, post.amount, post.account, permission)
            # se all'email inserita, non corrisponde nessuna autorizzazione...
            if result == -2:
                messages.info(request, 'ATTENTION! YOU DO NOT HAVE THE PERMISSION TO DO THAT')
                return render(request, 'transaction/post_edit.html', {'form': form})
            # se il tuo ordine non è stato esuguito del tutto per mancanza di compratori/venditori
            if result == 0:
                messages.info(request, 'GREAT! PART OF YOUR ORDER HAS BEEN EXECUTED!!! CHECK YOUR BALANCE')
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


# la funzione trasaction riceve dalla funzione post_news delle variabili e controlla se deve salvare o meno il post.
def transaction(price, type_of_transaction, user, amount, email_permission, permission):
    # contolla se ci sono errori di inserimento
    first = check_transaction(price, type_of_transaction, amount, permission)
    if first != 0:
        return first
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
    # se il database è vuoto lo popolo
    if len(Post.objects.values()) == 0:
        return 1
    recursion = 0
    # creo una lista di prezzi, ordinata in modo decrescente,fatta dagli ordini corrispondenti a buy_sell
    list_vett = sort_list(buy_sell)
    # scorro la lista
    for list in list_vett:
        # estraggo le informazioni che mi servono
        amounttr = list.get('amount')
        usertr = list.get('user_id')
        permission_post = list.get('account')
        type_of_tran = list.get('type_of_transaction')
        _id = list.get('_id')
        pricetr = list.get('price')
        # se la quantità inserita nell'ordine è pari o superiore a quella trovata in list
        # e si vuole effettuare un acquisto
        if float(price) >= float(pricetr) and type_of_transaction == 'BUY':
            # controllo se i destinatari della transazione (cioè coloro che posseggono le email insetite in account),
            # sono diversi
            if str(find_user(email_permission)) != str(find_user(permission_post)):
                # controllo che non ci siano dipendenze tra i soggetti destinatari della transazione
                if find_tangle(user, email_permission, usertr, permission_post) == 1:
                    # se le quantità da scambiare sono uguali
                    if float(amount) == float(amounttr):
                        final = float(amounttr)
                        # registro l'ordine
                        order(user, price, final, type_of_transaction, usertr, buy_sell, email_permission,
                              permission_post)
                        # cancello il post che ho incontrato
                        collection.remove({'_id': _id})
                        return 2
                    # se le quantità che si vuole scambiare è maggiore di quella incontrata
                    if float(amount) > float(amounttr):
                        final = float(amount) - float(amounttr)
                        order(user, price, amounttr, type_of_transaction, usertr, buy_sell, email_permission,
                              permission_post)
                        # cancello il post che ho incontrato
                        collection.remove({'_id': _id})
                        amount = final
                        recursion = 1
                    # se le quantità che si vuole scambiare è minore di quella incontrata
                    if float(amounttr) > float(amount):
                        final = float(amount)
                        order(user, price, final, type_of_transaction, usertr, buy_sell, email_permission,
                              permission_post)
                        amounttr = float(amounttr) - float(amount)
                        update_post(usertr, permission_post, amounttr, price, type_of_tran, _id)
                        return 2
    if recursion == 1:
        write_post(price, type_of_transaction, user, amount, email_permission)
        return 0
    # in tutti gli altri caso salvo il post
    return 1


# la funzione sort_list crea una lista di ordini ordinati secondo il prezzo, in modo decrescente, che hanno il parametro
# type_of_transaction == buy_sell
def sort_list(buy_sell):
    list_temp = []
    # richiamo il database
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['transaction_post']
    list = collection.aggregate([{'$sort': {"price": -1}}])
    for lis in list:
        if str(lis.get("type_of_transaction")) == buy_sell:
            list_temp.append(lis)
    return(list_temp)


# la funzione write_post scrive un nuovo post con i dati  ricevuti dalla funzione transaction
def write_post(price, type_of_transaction, user, amount, email_permission):
    # richiamo il database
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['transaction_post']
    post = {
        'user_id': user,
        'account': email_permission,
        'amount': amount,
        'price': price,
        'type_of_transaction': type_of_transaction,
        'datetime': datetime.datetime.now(),
    }
    collection.insert(post)


# la funzione update_post aggiorna il documento corrispondente all'_id assegnato
def update_post(usertr, permission_post, amount, price, type_of_tran, _id):
    # richiamo il database
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['transaction_post']
    post = {
        'user_id': usertr,
        'account': permission_post,
        'amount': amount,
        'price': price,
        'type_of_transaction': type_of_tran,
        'datetime': datetime.datetime.now(),
    }
    collection.update({'_id': _id}, post)


# la funzione find_tangle controlla che non ci siano dipendenze tra i soggetti della transazione.
# se ci sono dipendeze la transazione non va avanti
def find_tangle(user_a, email_post_a, user_b, email_post_b):
    # se i post sono scritti rispettivamente dai proprietari dell'email inserita
    if user_a == find_user(email_post_a) and user_b == find_user(email_post_b):
        # la transazione va avanti
        return 1
    else:
        # controllo che i soggetti coinvolti nel post inserito non abbiano concesso permessi ai soggetti coinvolti
        # nel post trovato. In user_id_list inserisco i soggetti convolti nel post inserito e in email_list i soggetti
        # coinvolti nel post trovato
        user_id_list = [user_a, find_user(email_post_a)]
        email_list = [find_email(user_b), email_post_b]
        for user in user_id_list:
            for email in email_list:
                if pass_tangle(user, email) == 0:
                    return 0
        # poichè devo controllare anche se i soggetti coinvolti nel post inserito abbiano ricevuto un'autorizzazione dai
        # soggetti del post incotrato, inverto le liste
        user_id_list = [user_b, find_user(email_post_b)]
        email_list = [find_email(user_a), email_post_a]
        for user in user_id_list:
            for email in email_list:
                if pass_tangle(user, email) == 0:
                    return 0
    # se non sono state trovate dipendenza la transazione va avanti
    return 1

#  la funzione pass_tangle controlla che nel profilo di user, non ci sia la email passata
def pass_tangle(user, email):
    list = []
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['app_profile']
    cursor = collection.find({'user_id': user})
    for cur in cursor:
        list.append(cur)
    for row in list:
        if str(email) in str(row.get('subprofile')):
            return 0
    else:
        return 1


#la funzione find_email recupera dall'used_id l'email corrispondente
def find_email(user):
    list_mail = []
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['app_profile']
    list = collection.find({'user_id':user})
    for lis in list:
        list_mail.append(lis)
    for find in list_mail:
        for split in find.get('ips'):
            return split.get('email')


# la funzione chceck_transaction controlla se ci sono errori nell'inserimento dell'ordine
def check_transaction(price, type_of_transaction, amount, permission):
    if price == None or amount == None:
        return 4
    # se l'utente ha inserito amount, o prezzo negativo il post non viene considerato
    if amount < 0 or price < 0:
        return 4
    if type_of_transaction == None:
        return 4
    # se l'utente ha il permesso solo di vendere
    if permission == 'sell':
        if type_of_transaction != 'SELL':
            return -2
    # se l'utente ha il permesso solo di acquistare
    if permission == 'buy':
        if type_of_transaction != 'BUY':
            return -2
    return 0


# la funzione check_fund controlla che i BTC inseriti nell'ordine di vendita, siano veramente nelle disponibilità dell'user
def check_funds(email_permission,amount):
    sell = 0.00
    list_wallet = []
    list_order = []
    user = find_user(email_permission)
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['authentication_btcwallet']
    # recupero i BTC regitrati nel wallet
    a=collection.aggregate([{'$match': {'user_id': user}}, {'$group': {'_id': '$user_id', 'total': {'$sum': '$wallet'}}}])
    for wallet in a:
        list_wallet.append(wallet)
    for i in list_wallet:
        # prendo i BTC totali posseduti dall'utente
        total = (i.get('total'))
    # recupero i BTC derivanti dai post con type_of_transaction == SELL
    collection = db['transaction_post']
    b = collection.find({'account': email_permission})
    for order in b:
        list_order.append(order)
    for i in list_order:
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
    list = collection.find()
    for find in list:
        a=str(find).split('subprofile')
        if str(email) in str(a[:-1]):
            return find.get('user_id')


# la funzione order registra la transazione nel profilo dei due utenti e invoca la funzione update_wallet per aggiornare i wallets
# (ipotizzo che non ci siano limiti di moneta fiat)
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
        'subprofile': user_account,
        'price': price,
        'amount': final,
        'updated': datetime.datetime.now()
    }
    # ordine dell'utente che ha inserito l'ultimo post
    collection.insert(post1)

    post2 = {
        'profile': usertr,
        'buy_sell': buy_sell,
        'subprofile': usert_account,
        'price': price,
        'amount': final,
        'updated': datetime.datetime.now()
    }
    # ordine dell'utente dell'altro post
    collection.insert(post2)
    # aggiorna i wallet degli utenti
    update_wallet(final, type_of_transaction, user_account, price, permission_post)


# la funzione upadate_wallet aggiorna i wallets dei due utenti andando a registrare in autentication_btcwallet tutte le
# transazioni
def update_wallet(final, type_of_transaction, user_account, price, permission_post):
    # recupero l'user_id dell'altro utente
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
        'price': price,
        'updated': datetime.datetime.now()
    }
    # aggiornamento per il compratore
    collection.insert(post_buy)

    post_sell = {
        'user_id': sell_user,
        'wallet': -final,
        'price': price,
        'updated': datetime.datetime.now()
    }
    # aggiornamento per il veditore
    collection.insert(post_sell)


# la funzione permission_request prende da imput l'email con la quale si vuole effettuare l'ordine
def permission_request(email, id, my_mail):
    # invoca la funzione mongodb_search per verificare l'email inserita dall'utente
    response = mongodb_search(email, id, my_mail)
    return response


# la funzione mongobd_search controlla se l'email inserita ha garantito un permesso all'utente. In alternativa gli
# restituisce un errore
def mongodb_search(email, id, my_mail):
    list_mongo = []
    mongo = MongoClient(port=27017)
    # qui va il nome del database (nel mio caso 'engine')
    db = mongo['engine']
    collection = db['app_profile']
    # creo un cursore in mongodb per trovare l'email dell'utente contenuta in ips
    mongo=collection.find({'ips.email': email})
    for list in mongo:
        list_mongo.append(list)
    # creo una 'lista' prendendo le informazioni del prfilo degli utenti (non uso mongodb direttamente)
    user_mail = User.objects.values()
    # per ogni utente vado a scorrere la 'lista'
    for row in user_mail:
        # se trova che la mail inserita dall'utente corrisponde alla email dell'utente stesso
        if str(email) == row.get('email'):
            return 'self'
    print(str(email), row.get('email'))
    # scorro la lista list_mongo, per cercare se nella sezione subprofile dell'utente corrispondente alla email
    # inserita, esiste l'email dell'utente che scrive e il tipo di permesso concesso
    for subprofile in list_mongo:
        for elem in subprofile.get('subprofile'):
            if str(my_mail) == str(elem.get('email')) and 'buy' == str(elem.get('permission')):
                return 'buy'
            if str(my_mail) == str(elem.get('email')) and 'all' == str(elem.get('permission')):
                return 'all'
            if str(my_mail) == str(elem.get('email')) and 'sell' == str(elem.get('permission')):
                return 'sell'
    # se non ci sono permessi concessi restitusce Deny
    return 'Deny'
