from queue import Empty
from django.shortcuts import render, redirect
from PreviewApp.models import Technical, MappedTechnical

from core import settings
import os
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .utilities import updatepaymentadvice, updateremittanceallocation, updatenonpairedreceipt
from datetime import datetime,date,timedelta


from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, HttpResponseNotFound
import re
from account.signals import custom_receiver
from account.models import UserActivityLog

# Create your views here.
@login_required(login_url='account:login')
def home(request):
    user = request.user
    country = user.country

    
    if user.is_admin:
        technical_receipts = Technical.objects.filter(
        Category__icontains="Receipt")
        mappedtechnical_receipts = MappedTechnical.objects.filter(
        Category__icontains="Receipt")

        mappedtechnical_paymentadvise = MappedTechnical.objects.filter(
        Office__icontains=country, Category__icontains="Payment Advice")
    else:
        technical_receipts = Technical.objects.filter(
                Company__icontains=country, Category__icontains="Receipt")
        mappedtechnical_receipts = MappedTechnical.objects.filter(
            Office__icontains=country, Category__icontains="Receipt")

        mappedtechnical_paymentadvise = MappedTechnical.objects.filter(
            Office__icontains=country, Category__icontains="Payment Advice")

    total_receipts = int(technical_receipts.count()) + \
        int(mappedtechnical_receipts.count())

    context = {

        'technical_receipts': technical_receipts,
        'mappedtechnical_receipts': mappedtechnical_receipts,
        'total_receipts': total_receipts,
        'mappedtechnical_paymentadvise': mappedtechnical_paymentadvise,
    }
    return render(request, 'home.html', context)

# @login_required(login_url='account:login')
# def latest_receipts(request):

#     user = request.user
#     country = user.country
#     mailer = False
#     paymentadvices = False
#     receipts = True
#     remittanceallocations = False
#     datetoday=date.today()
#     newdatetoday= datetoday + timedelta(days=5)
#     # date_3days_ago=datetoday - timedelta(days=5)



#     # if user.is_admin:
#     #     latest_receipts = Technical.objects.filter(
#     #         Category__icontains='Receipt',ValueDate__lte=newdatetoday).order_by('-id')[:20]
        

#     #     # All Receipt count fo admin users
#     #     all_receipts = Technical.objects.filter(Category__icontains='Receipt')

#     #     context = {
#     #         'mailer': mailer,
#     #         'paymentadvices': paymentadvices,
#     #         'receipts': receipts,
#     #         'remittanceallocations': remittanceallocations,
#     #         'latest_receipts': latest_receipts,
#     #         'all_receipts': all_receipts,

#     #     }
#     #     return render(request, 'latest_receipts.html', context)

#     latest_receipts = Technical.objects.filter(
#         Company__icontains=country, Category__icontains='Receipt',ValueDate__lte=newdatetoday).order_by('-id')[:20]

#     all_receipts = Technical.objects.filter(Category__icontains='Receipt')

#     context = {
#         'mailer': mailer,
#         'paymentadvices': paymentadvices,
#         'receipts': receipts,
#         'remittanceallocations': remittanceallocations,
#         'latest_receipts': latest_receipts,
#         'all_receipts': all_receipts,
#     }
#     return render(request, 'latest_receipts.html', context)
@login_required(login_url='account:login')
def latest_receipts(request):
    user = request.user
    country = user.country
    mailer = False
    paymentadvices = False
    receipts = True
    remittanceallocations = False
    datetoday = date.today()
    # newdatetoday = datetoday + timedelta(days=5)
    newdateyesterday = datetoday - timedelta(days=1)
    if user.is_admin:
        latest_receipts = Technical.objects.filter(
            Category__icontains='Receipt', CreatedDate__icontains=newdateyesterday
        ).order_by('-id')

        all_receipts = Technical.objects.filter(Category__icontains='Receipt').count()
    else:
        latest_receipts = Technical.objects.filter(
            Company__icontains=country, Category__icontains='Receipt', CreatedDate__icontains=newdateyesterday
        ).order_by('-id')

        all_receipts = Technical.objects.filter(Company__icontains=country,Category__icontains='Receipt').count()
    

    context = {
        'mailer': mailer,
        'paymentadvices': paymentadvices,
        'receipts': receipts,
        'remittanceallocations': remittanceallocations,
        'latest_receipts': latest_receipts,
        'all_receipts': all_receipts,
    }
    return render(request, 'latest_receipts.html', context)

# @login_required(login_url='account:login')
# def latest_remittance_allocations(request):

#     user = request.user
#     country = user.country
#     mailer = False
#     paymentadvices = False
#     receipts = False
#     remittanceallocations = True
#     datetoday=date.today()
#     newdatetoday= datetoday + timedelta(days=5)
#     # date_3days_ago=datetoday - timedelta(days=5)

#     if user.is_admin:

#         latest_remittance_allocations = MappedTechnical.objects.filter(
#            Category__icontains='Receipt',ValueDate__lte=newdatetoday).order_by('-id')[:20]

#         # All Receipt count fo admin users
#         all_remittance_allocations = MappedTechnical.objects.filter(
#             Category__icontains='Receipt')

#         context = {

#             'mailer': mailer,
#             'paymentadvices': paymentadvices,
#             'receipts': receipts,
#             'remittanceallocations': remittanceallocations,
#             'latest_remittance_allocations': latest_remittance_allocations,
#             'all_remittance_allocations': all_remittance_allocations,

#         }
#         return render(request, 'latest_ra.html', context)

#     latest_remittance_allocations = MappedTechnical.objects.filter(
#         Office__icontains=country, Category__icontains='Receipt',ValueDate__lte=newdatetoday).order_by('-id')[:20]

#     all_remittance_allocations = MappedTechnical.objects.filter(
#         Category__icontains='Receipt')

#     context = {

#         'mailer': mailer,
#         'paymentadvices': paymentadvices,
#         'receipts': receipts,
#         'remittanceallocations': remittanceallocations,
#         'latest_remittance_allocations': latest_remittance_allocations,
#         'all_remittance_allocations': all_remittance_allocations,

#     }
#     return render(request, 'latest_ra.html', context)
@login_required(login_url='account:login')
def latest_remittance_allocations(request):
    user = request.user
    country = user.country
    mailer = False
    paymentadvices = False
    receipts = False
    remittanceallocations = True
    datetoday = date.today()
    # newdatetoday = datetoday + timedelta(days=5)
    newdateyesterday = datetoday - timedelta(days=1)
    if user.is_admin:
        latest_remittance_allocations = MappedTechnical.objects.filter(
            Category__icontains='Receipt', CreatedDate__icontains=newdateyesterday
        ).order_by('-id')

        all_remittance_allocations = MappedTechnical.objects.filter(
            Category__icontains='Receipt'
        ).count()
    else:
        latest_remittance_allocations = MappedTechnical.objects.filter(
            Office__icontains=country, Category__icontains='Receipt', CreatedDate__icontains=newdateyesterday
        ).order_by('-id')

        all_remittance_allocations = MappedTechnical.objects.filter(
            Office__icontains=country, Category__icontains='Receipt'
        ).count()

    context = {
        'mailer': mailer,
        'paymentadvices': paymentadvices,
        'receipts': receipts,
        'remittanceallocations': remittanceallocations,
        'latest_remittance_allocations': latest_remittance_allocations,
        'all_remittance_allocations': all_remittance_allocations,
    }

    return render(request, 'latest_ra.html', context)

# @login_required(login_url='account:login')
# def latest_payment_advices(request):
  
#     user = request.user
#     country = user.country
#     mailer = False
#     paymentadvices = True
#     receipts = False
#     remittanceallocations = False
#     datetoday=date.today()
#     newdatetoday= datetoday + timedelta(days=5)
#     # date_3days_ago=datetoday - timedelta(days=5)

#     if user.is_admin:

#         latest_payment_advices = MappedTechnical.objects.filter(
#             Category__icontains='Payment Advice',ValueDate__lte=newdatetoday).order_by('-id')[:20]


#         # All Receipt count fo admin users

#         all_payment_advices = MappedTechnical.objects.filter(
#             Category__icontains='Payment Advice')

#         context = {

#             'mailer': mailer,
#             'paymentadvices': paymentadvices,
#             'receipts': receipts,
#             'remittanceallocations': remittanceallocations,
#             'latest_payment_advices': latest_payment_advices,
#             'all_payment_advices': all_payment_advices,

#         }
#         return render(request, 'latest_pa.html', context)
     
#     latest_payment_advices = MappedTechnical.objects.filter(
#         Office__icontains=country, Category__icontains='Payment Advice',ValueDate__lte=newdatetoday).order_by('-id')[:20]
   

#     all_payment_advices = MappedTechnical.objects.filter(
#         Office__icontains=country, Category__icontains='Payment Advice')

#     context = {
#         'mailer': mailer,
#         'paymentadvices': paymentadvices,
#         'receipts': receipts,
#         'remittanceallocations': remittanceallocations,
#         'latest_payment_advices': latest_payment_advices,
#         'all_payment_advices': all_payment_advices,

#     }
#     return render(request, 'latest_pa.html', context)

@login_required(login_url='account:login')
def latest_payment_advices(request):
    user = request.user
    country = user.country
    datetoday = date.today()
    # newdatetoday = datetoday + timedelta(days=5)
    newdateyesterday = datetoday - timedelta(days=1)

    if user.is_admin:
        latest_payment_advices = MappedTechnical.objects.filter(Category__icontains='Payment Advice', CreatedDate__icontains= newdateyesterday).order_by('-id')
        all_payment_advices = MappedTechnical.objects.filter(Category__icontains= 'Payment Advice').count()
    else:
        latest_payment_advices = MappedTechnical.objects.filter(Office__icontains=country,Category__icontains='Payment Advice', CreatedDate__icontains= newdateyesterday).order_by('-id')
        all_payment_advices = MappedTechnical.objects.filter(Office__icontains=country,Category__icontains= 'Payment Advice').count()

    context = {
        'mailer': False,
        'paymentadvices': True,
        'receipts': False,
        'remittanceallocations': False,
        'latest_payment_advices': latest_payment_advices,
        'all_payment_advices': all_payment_advices,
    }

    return render(request, 'latest_pa.html', context)

@login_required(login_url='account:login')
def PreviewReceipt(request, foo):
 
    user = request.user
    country = user.country
    mailer = False
    paymentadvices = False
    receipts = False
    remittanceallocations = False

    if user.is_admin:
        technical = Technical.objects.filter(ReceiptNumber__icontains=foo)
        mappedtechnical = MappedTechnical.objects.filter(
            ReceiptNumber__icontains=foo)
        filename = foo + ".pdf"
        filepath = os.path.join(settings.FILES_DIR, filename)
        if mappedtechnical:
            for i in mappedtechnical:
                doctype = i.Category
        if technical:
            for i in technical:
                doctype = i.Category

        context = {
            'mailer': mailer,
            'paymentadvices': paymentadvices,
            'receipts': receipts,
            'remittanceallocations': remittanceallocations,
            'doctype': doctype,
            'filepath': filepath,
            'technical': technical,
            'mappedtechnical': mappedtechnical,
            'receipt_number': foo,
        }

        return render(request, 'preview.html', context)

    technical = Technical.objects.filter(
        ReceiptNumber__icontains=foo,
        Company__icontains=country)
    mappedtechnical = MappedTechnical.objects.filter(
        ReceiptNumber__icontains=foo, Office__icontains=country)

    filename = foo + ".pdf"
    filepath = os.path.join(settings.FILES_DIR, filename)

    context = {
        'mailer': mailer,
        'paymentadvices': paymentadvices,
        'receipts': receipts,
        'remittanceallocations': remittanceallocations,
        'filepath': filepath,
        'technical': technical,
        'mappedtechnical': mappedtechnical,
        'receipt_number': foo,
    }

    return render(request, 'preview.html', context)


# @login_required(login_url='account:login')
# def SearchReceipt(request):

#     user = request.user
#     country = user.country
#     search = True

#     if request.method == 'GET':
#         search = request.GET.get('search')
#         query = search.strip()
#         mailer = False

#         if user.is_admin:
#             if query:
#                 lookups2 = Q(
#                     PaymentPartner__icontains=query) | Q(
#                     BankID__icontains=query) | Q(
#                     BankName__icontains=query) | Q(
#                     BankAccountNo__icontains=query) | Q(
#                     BankAccountCurrencyCode__icontains=query) | Q(
#                         OriginalCurrencyCode__icontains=query) | Q(
#                             BalanceOriginal__icontains=query) | Q(
#                                 BalanceOutstandingOriginal__icontains=query) | Q(
#                                     RemittanceDirection__icontains=query) | Q(
#                                         RemittanceStatus__icontains=query) | Q(
#                                             Company__icontains=query) | Q(
#                                                 ReceiptNumber__icontains=query) | Q(
#                                                     ReceiverEmail__icontains=query) | Q(
#                                                         CreatedDate__icontains=query) | Q(
#                                                             Category__icontains=query)
#                 technical_search_result = Technical.objects.filter(
#                     lookups2)
#                 lookups3 = Q(
#                     BusinessPartner__icontains=query) | Q(
#                     ReceiptNumber__icontains=query) | Q(
#                     Currency__icontains=query) | Q(
#                     Amount__icontains=query) | Q(
#                     BalanceUnsettledAmount__icontains=query) | Q(
#                         PaymentType__icontains=query) | Q(
#                             Office__icontains=query) | Q(
#                                 WorkSheetId__icontains=query) | Q(
#                                     Category__icontains=query)
#                 mappedtechnical_search_result = MappedTechnical.objects.filter(
#                     lookups3).distinct()
#                 context = {
#                     'user': user,
#                     'mailer': mailer,
#                     'search': search,
#                     'technical_search_result': technical_search_result,
#                     'mappedtechnical_search_result': mappedtechnical_search_result,
#                     'submitbutton': query}
#                 if technical_search_result or mappedtechnical_search_result:
#                     return render(request, 'search.html', context)
#                 messages.info(request, "No results found!")
#                 return render(request, 'search.html', context)

#         if query:
#             lookups2 = Q(
#                 PaymentPartner__icontains=query) | Q(
#                 BankID__icontains=query) | Q(
#                 BankName__icontains=query) | Q(
#                 BankAccountNo__icontains=query) | Q(
#                     BankAccountCurrencyCode__icontains=query) | Q(
#                         OriginalCurrencyCode__icontains=query) | Q(
#                             BalanceOriginal__icontains=query) | Q(
#                                 BalanceOutstandingOriginal__icontains=query) | Q(
#                                     RemittanceDirection__icontains=query) | Q(
#                                         RemittanceStatus__icontains=query) | Q(
#                                             Company__icontains=query) | Q(
#                                                 ReceiptNumber__icontains=query) | Q(
#                                                     ReceiverEmail__icontains=query) | Q(
#                                                         CreatedDate__icontains=query)
#             technical_search_result = Technical.objects.filter(
#                 lookups2, Company__icontains=country).distinct().order_by('-id')
#             lookups3 = Q(
#                 BusinessPartner__icontains=query) | Q(
#                 ReceiptNumber__icontains=query) | Q(
#                 Currency__icontains=query) | Q(
#                 Amount__icontains=query) | Q(
#                     BalanceUnsettledAmount__icontains=query) | Q(
#                         PaymentType__icontains=query) | Q(
#                             Office__icontains=query) | Q(
#                                 WorkSheetId__icontains=query)
#             mappedtechnical_search_result = MappedTechnical.objects.filter(
#                 lookups3, Office__icontains=country).distinct().order_by('-id')
#             context = {
#                 'user': user,
#                 'search': search,
#                 'mailer': mailer,
#                 'technical_search_result': technical_search_result,
#                 'mappedtechnical_search_result': mappedtechnical_search_result,
#                 'submitbutton': query
#             }
#             if technical_search_result or mappedtechnical_search_result:
#                 return render(request, 'search.html', context)
#             messages.info(request, "No results found!")
#             return render(request, 'search.html', context)

#         else:
#             messages.warning(request, "no search phrase entered!")
#             return render(request, 'search.html')
#     else:
#         return render(request, 'search.html')
# @login_required(login_url='account:login')
# def SearchReceipt(request):
#     user = request.user
#     country = user.country
#     search = request.GET.get('search')
#     mailer = False

#     if request.method == 'GET' and search:
#         query = search.strip()

#         if user.is_admin:
#             lookups2 = Q(
#                 PaymentPartner__icontains=query) | Q(
#                 BankID__icontains=query) | Q(
#                 BankName__icontains=query) | Q(
#                 BankAccountNo__icontains=query) | Q(
#                 BankAccountCurrencyCode__icontains=query) | Q(
#                 OriginalCurrencyCode__icontains=query) | Q(
#                 BalanceOriginal__icontains=query) | Q(
#                 BalanceOutstandingOriginal__icontains=query) | Q(
#                 RemittanceDirection__icontains=query) | Q(
#                 RemittanceStatus__icontains=query) | Q(
#                 Company__icontains=query) | Q(
#                 ReceiptNumber__icontains=query) | Q(
#                 ReceiverEmail__icontains=query) | Q(
#                 CreatedDate__icontains=query) | Q(
#                 Category__icontains=query)
#             technical_search_result = Technical.objects.filter(lookups2)
#             lookups3 = Q(
#                 BusinessPartner__icontains=query) | Q(
#                 ReceiptNumber__icontains=query) | Q(
#                 Currency__icontains=query) | Q(
#                 Amount__icontains=query) | Q(
#                 BalanceUnsettledAmount__icontains=query) | Q(
#                 PaymentType__icontains=query) | Q(
#                 Office__icontains=query) | Q(
#                 WorkSheetId__icontains=query) | Q(
#                 Category__icontains=query)
#             mappedtechnical_search_result = MappedTechnical.objects.filter(lookups3).distinct()
#         else:
#             lookups2 = Q(
#                 PaymentPartner__icontains=query) | Q(
#                 BankID__icontains=query) | Q(
#                 BankName__icontains=query) | Q(
#                 BankAccountNo__icontains=query) | Q(
#                 BankAccountCurrencyCode__icontains=query) | Q(
#                 OriginalCurrencyCode__icontains=query) | Q(
#                 BalanceOriginal__icontains=query) | Q(
#                 BalanceOutstandingOriginal__icontains=query) | Q(
#                 RemittanceDirection__icontains=query) | Q(
#                 RemittanceStatus__icontains=query) | Q(
#                 Company__icontains=query) | Q(
#                 ReceiptNumber__icontains=query) | Q(
#                 ReceiverEmail__icontains=query) | Q(
#                 CreatedDate__icontains=query)
#             technical_search_result = Technical.objects.filter(
#                 lookups2, Company__icontains=country).distinct().order_by('-id')
#             lookups3 = Q(
#                 BusinessPartner__icontains=query) | Q(
#                 ReceiptNumber__icontains=query) | Q(
#                 Currency__icontains=query) | Q(
#                 Amount__icontains=query) | Q(
#                 BalanceUnsettledAmount__icontains=query) | Q(
#                 PaymentType__icontains=query) | Q(
#                 Office__icontains=query) | Q(
#                 WorkSheetId__icontains=query)
#             mappedtechnical_search_result = MappedTechnical.objects.filter(
#                 lookups3, Office__icontains=country).distinct().order_by('-id')
        
#         context = {
#             'user': user,
#             'search': search,
#             'mailer': mailer,
#             'technical_search_result': technical_search_result,
#             'mappedtechnical_search_result': mappedtechnical_search_result,
#             'submitbutton': query
#         }
        
#         if technical_search_result or mappedtechnical_search_result:
#             return render(request, 'search.html', context)
#         messages.info(request, "No results found!")
#         return render(request, 'search.html', context)
#     else:
#         messages.warning(request, "No search phrase entered!")
#         return render(request, 'search.html')
@login_required(login_url='account:login')
def SearchReceipt(request):
    user = request.user
    country = user.country
    search = request.GET.get('search')
    mailer = False

    if request.method == 'GET' and search:
        query = search.strip()
        technical_search_result = None
        mappedtechnical_search_result = None

        if user.is_admin:
            technical_search_result = Technical.objects.filter(
                Q(PaymentPartner__icontains=query) | Q(BankID__icontains=query) | Q(BankName__icontains=query) | 
                Q(BankAccountNo__icontains=query) | Q(BankAccountCurrencyCode__icontains=query) | 
                Q(OriginalCurrencyCode__icontains=query) | Q(BalanceOriginal__icontains=query) | 
                Q(BalanceOutstandingOriginal__icontains=query) | Q(RemittanceDirection__icontains=query) | 
                Q(RemittanceStatus__icontains=query) | Q(Company__icontains=query) | 
                Q(ReceiptNumber__icontains=query) | Q(ReceiverEmail__icontains=query) | 
                Q(Category__icontains=query)
            )
            mappedtechnical_search_result = MappedTechnical.objects.filter(
                Q(BusinessPartner__icontains=query) | Q(ReceiptNumber__icontains=query) | 
                Q(Currency__icontains=query) | Q(Amount__icontains=query) | 
                Q(BalanceUnsettledAmount__icontains=query) | Q(PaymentType__icontains=query) | 
                Q(Office__icontains=query) | Q(WorkSheetId__icontains=query) | 
                Q(Category__icontains=query)
            ).distinct()
        else:
            technical_search_result = Technical.objects.filter(
                Q(PaymentPartner__icontains=query) | Q(BankID__icontains=query) | Q(BankName__icontains=query) | 
                Q(BankAccountNo__icontains=query) | Q(BankAccountCurrencyCode__icontains=query) | 
                Q(OriginalCurrencyCode__icontains=query) | Q(BalanceOriginal__icontains=query) | 
                Q(BalanceOutstandingOriginal__icontains=query) | Q(RemittanceDirection__icontains=query) | 
                Q(RemittanceStatus__icontains=query) | Q(Company__icontains=query) | 
                Q(ReceiptNumber__icontains=query) | Q(ReceiverEmail__icontains=query),
                Company__icontains=country
            ).distinct().order_by('-id')
            mappedtechnical_search_result = MappedTechnical.objects.filter(
                Q(BusinessPartner__icontains=query) | Q(ReceiptNumber__icontains=query) | 
                Q(Currency__icontains=query) | Q(Amount__icontains=query) | 
                Q(BalanceUnsettledAmount__icontains=query) | Q(PaymentType__icontains=query) | 
                Q(Office__icontains=query) | Q(WorkSheetId__icontains=query)
            ).distinct().order_by('-id')
        
        context = {
            'user': user,
            'search': search,
            'mailer': mailer,
            'technical_search_result': technical_search_result,
            'mappedtechnical_search_result': mappedtechnical_search_result,
            'submitbutton': query
        }
        
        if technical_search_result or mappedtechnical_search_result:
            return render(request, 'search.html', context)
        
        messages.info(request, "No results found!")
    
    else:
        messages.warning(request, "No search phrase entered!")

    return render(request, 'search.html')

@login_required(login_url='account:login')
def advancedsearch(request):    
    user = request.user
    company = user.country
    search = True
    mailer = False
    preparedbylist = []

    if user.is_admin:
        newlist = MappedTechnical.objects.filter()
    else:
        newlist = MappedTechnical.objects.filter(Office__icontains=company)

    for i in newlist:

        if i.IssuedBy and i.IssuedBy not in preparedbylist and i.IssuedBy is not None and i.IssuedBy != " ":
            preparedbylist.append(i.IssuedBy)

    startdate = request.GET.get('start-date')
    enddate = request.GET.get('end-date')
    organization = request.GET.get('organization')
    doctype = request.GET.get('doctype')
    Issuedby = request.GET.get('preparedby')
    searchphrase = request.GET.get('search')
    classname = request.GET.get('classname')

    todaysdate = str(date.today())

    d3 = datetime.strptime(todaysdate, "%Y-%m-%d") + timedelta(days=1)
    d1 = ""
    d2 = ""
    format_sd = ""
    format_ed = ""
    ib = ""
    sp = ""
    dt = ""
    oz = ""

    if not startdate and enddate:
        messages.error(request, "Please selest a start date!")
        return render(request, 'advancedsearch.html')

    # Check dates/date range error handling
    if startdate:
        format_sd = datetime.strptime(startdate, "%Y-%m-%d")
        if enddate:
            format_ed = datetime.strptime(enddate, "%Y-%m-%d")

            if format_sd > format_ed:
                messages.error(
                    request, "start date is greater than the enddate!")
                return render(request, 'advancedsearch.html')

            d1 = startdate
            d2 = format_ed + timedelta(days=1)
        else:
            if format_sd > d3:
                messages.error(
                    request, "start date is greater than todays date!")
                return render(request, 'advancedsearch.html')

            d1 = startdate
            d2 = None
    else:
        if enddate:
            format_ed = datetime.strptime(enddate, "%Y-%m-%d")

            d1 = None
            d2 = format_ed + + timedelta(days=1)
        else:
            d2 = None
            d1 = None

    # Assign filter dates
    sd = d1
    ed = d2

    # Assign filter parameters
    if Issuedby:

        if Issuedby == "All":
            ib = None
        else:
            ib = Issuedby
    else:
        ib = None

    if searchphrase:

        if searchphrase == "All":
            sp = None
        else:
            sp = searchphrase
    else:
        sp = None

    if doctype:

        if doctype == "All":
            dt = None
        else:
            dt = doctype
    else:
        dt = None

    if organization:

        if organization == "All":
            oz = None
        else:
            oz = organization
    else:
        oz = None

    if sp:
        query = sp.strip()
        technical_lookup = Q(
            PaymentPartner__icontains=query) | Q(
            BankID__icontains=query) | Q(
            BankName__icontains=query) | Q(
                BankAccountNo__icontains=query) | Q(
                    BankAccountCurrencyCode__icontains=query) | Q(
                        OriginalCurrencyCode__icontains=query) | Q(
                            BalanceOriginal__icontains=query) | Q(
                                BalanceOutstandingOriginal__icontains=query) | Q(
                                    RemittanceDirection__icontains=query) | Q(
                                        RemittanceStatus__icontains=query) | Q(
                                            Company__icontains=query) | Q(
                                                ReceiptNumber__icontains=query) | Q(
                                                    ReceiverEmail__icontains=query) | Q(
                                                        CreatedDate__icontains=query) | Q(
                                                            Category__icontains=query)
        mappedtechnical_lookup = Q(
            BusinessPartner__icontains=query) | Q(
            ReceiptNumber__icontains=query) | Q(
            Currency__icontains=query) | Q(
                Amount__icontains=query) | Q(
                    BalanceUnsettledAmount__icontains=query) | Q(
                        PaymentType__icontains=query) | Q(
                            Office__icontains=query) | Q(
                                WorkSheetId__icontains=query) | Q(
                                    Category__icontains=query)

    # ADMIN USER
    if user.is_admin:
        if sd and ed:
            # filter all
            if ib and sp and dt and oz:
                technical_search_result = Technical.objects.filter(
                    technical_lookup,
                    CreatedDate__range=[
                        sd,
                        ed],
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    Company__icontains=oz).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup,
                    CreatedDate__range=[
                        sd,
                        ed],
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    Office__icontains=oz).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'classname': classname,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter phrase, doctype & organization
            if not ib and sp and dt and oz:
                technical_search_result = Technical.objects.filter(
                    technical_lookup, CreatedDate__range=[
                        sd, ed], Category__icontains=dt, Company__icontains=oz).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup, CreatedDate__range=[
                        sd, ed], Category__icontains=dt, Office__icontains=oz).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter doctype & organization
            if not ib and not sp and dt and oz:
                if dt == 'Payement Advice':
                    technical_search_result = Technical.objects.filter(
                        ReceiptNumber__startswith='PA', CreatedDate__range=[
                            sd, ed], Company__icontains=oz).distinct().order_by('-id')
                    mappedtechnical_search_result = MappedTechnical.objects.filter(
                        Category__icontains=dt, CreatedDate__range=[
                            sd, ed], Office__icontains=oz).distinct().order_by('-id')
               
                technical_search_result = Technical.objects.filter(
                    Category__icontains=dt, CreatedDate__range=[
                        sd, ed], Company__icontains=oz).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    Category__icontains=dt, CreatedDate__range=[
                        sd, ed], Office__icontains=oz).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter organization
            if not ib and not sp and not dt and oz:
                technical_search_result = Technical.objects.filter(
                    Company__icontains=oz, CreatedDate__range=[sd, ed]).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    Office__icontains=oz, CreatedDate__range=[sd, ed]).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter none
            if not ib and not sp and not dt and not oz:
                technical_search_result = Technical.objects.filter(
                    CreatedDate__range=[sd, ed]).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    CreatedDate__range=[sd, ed]).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter IssuedBy
            if ib and not sp and not dt and not oz:
                technical_search_result = Technical.objects.filter(
                    IssuedBy__icontains=ib, CreatedDate__range=[sd, ed]).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    IssuedBy__icontains=ib, CreatedDate__range=[sd, ed]).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter IssuedBy & phrase
            if ib and sp and not dt and not oz:
                technical_search_result = Technical.objects.filter(
                    technical_lookup, IssuedBy__icontains=ib, CreatedDate__range=[sd, ed]).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup, IssuedBy__icontains=ib, CreatedDate__range=[
                        sd, ed]).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter IssuedBy,phrase & doctype
            if ib and sp and dt and not oz:
                technical_search_result = Technical.objects.filter(
                    technical_lookup,
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    CreatedDate__range=[
                        sd,
                        ed]).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup,
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    CreatedDate__range=[
                        sd,
                        ed]).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter phrase & organization
            if not ib and sp and not dt and oz:
                technical_search_result = Technical.objects.filter(
                    technical_lookup, Company__icontains=oz, CreatedDate__range=[sd, ed]).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup, Office__icontains=oz, CreatedDate__range=[sd, ed]).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter IssuedBy,phrase & doctype
            if ib and not sp and dt and not oz:
                technical_search_result = Technical.objects.filter(
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    CreatedDate__range=[
                        sd,
                        ed]).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    IssuedBy__icontains=ib, Category__icontains=dt, CreatedDate__range=[
                        sd, ed]).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter phrase
            if not ib and sp and not dt and not oz:
                technical_search_result = Technical.objects.filter(
                    technical_lookup, CreatedDate__range=[sd, ed]).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup, CreatedDate__range=[sd, ed]).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter dt
            if not ib and not sp and dt and not oz:
                technical_search_result = Technical.objects.filter(
                    Category__icontains=dt, CreatedDate__range=[sd, ed]).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    Category__icontains=dt, CreatedDate__range=[sd, ed]).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)

        if sd and not ed:
            # filter all
            if ib and sp and dt and oz:
                technical_search_result = Technical.objects.filter(
                    technical_lookup,
                    CreatedDate__range=[
                        sd,
                        d3],
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    Company__icontains=oz).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup,
                    CreatedDate__range=[
                        sd,
                        d3],
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    Office__icontains=oz).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter phrase, doctype & organization
            if not ib and sp and dt and oz:
                technical_search_result = Technical.objects.filter(
                    technical_lookup, CreatedDate__range=[
                        sd, d3], Category__icontains=dt, Company__icontains=oz).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup, CreatedDate__range=[
                        sd, d3], Category__icontains=dt, Office__icontains=oz).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter doctype & organization
            if not ib and not sp and dt and oz:
                technical_search_result = Technical.objects.filter(
                    Category__icontains=dt, CreatedDate__range=[
                        sd, d3], Company__icontains=oz).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    Category__icontains=dt, CreatedDate__range=[
                        sd, d3], Office__icontains=oz).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter organization
            if not ib and not sp and not dt and oz:
                technical_search_result = Technical.objects.filter(
                    Company__icontains=oz, CreatedDate__range=[sd, d3]).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    Office__icontains=oz, CreatedDate__range=[sd, d3]).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter none
            if not ib and not sp and not dt and not oz:
                technical_search_result = Technical.objects.filter(
                    CreatedDate__range=[sd, d3]).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    CreatedDate__range=[sd, d3]).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter IssuedBy
            if ib and not sp and not dt and not oz:
                technical_search_result = Technical.objects.filter(
                    IssuedBy__icontains=ib, CreatedDate__range=[sd, d3]).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    IssuedBy__icontains=ib, CreatedDate__range=[sd, d3]).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter IssuedBy & phrase
            if ib and sp and not dt and not oz:
                technical_search_result = Technical.objects.filter(
                    technical_lookup, IssuedBy__icontains=ib, CreatedDate__range=[sd, d3]).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup, IssuedBy__icontains=ib, CreatedDate__range=[
                        sd, d3]).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter IssuedBy,phrase & doctype
            if ib and sp and dt and not oz:
                technical_search_result = Technical.objects.filter(
                    technical_lookup,
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    CreatedDate__range=[
                        sd,
                        d3]).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup,
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    CreatedDate__range=[
                        sd,
                        d3]).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter phrase & organization
            if not ib and sp and not dt and oz:
                technical_search_result = Technical.objects.filter(
                    technical_lookup, Company__icontains=oz, CreatedDate__range=[sd, d3]).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup, Office__icontains=oz, CreatedDate__range=[sd, d3]).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'classname': classname,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter IssuedBy,phrase & doctype
            if ib and not sp and dt and not oz:
                technical_search_result = Technical.objects.filter(
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    CreatedDate__range=[
                        sd,
                        d3]).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    IssuedBy__icontains=ib, Category__icontains=dt, CreatedDate__range=[
                        sd, d3]).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter phrase
            if not ib and sp and not dt and not oz:
                technical_search_result = Technical.objects.filter(
                    technical_lookup, CreatedDate__range=[sd, d3]).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup, CreatedDate__range=[sd, d3]).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter dt
            if not ib and not sp and dt and not oz:
                technical_search_result = Technical.objects.filter(
                    Category__icontains=dt, CreatedDate__range=[sd, d3]).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    Category__icontains=dt, CreatedDate__range=[sd, d3]).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)

        else:
            # filter all
            if ib and sp and dt and oz:
                technical_search_result = Technical.objects.filter(
                    technical_lookup,
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    Company__icontains=oz).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup,
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    Office__icontains=oz).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter phrase, doctype & organization
            if not ib and sp and dt and oz:
                technical_search_result = Technical.objects.filter(
                    technical_lookup, Category__icontains=dt, Company__icontains=oz).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup, Category__icontains=dt, Office__icontains=oz).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter doctype & organization
            if not ib and not sp and dt and oz:
                technical_search_result = Technical.objects.filter(
                    Category__icontains=dt, Company__icontains=oz).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    Category__icontains=dt, Office__icontains=oz).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter organization
            if not ib and not sp and not dt and oz:
                technical_search_result = Technical.objects.filter(
                    Company__icontains=oz).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    Office__icontains=oz).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter none
            if not ib and not sp and not dt and not oz:
                technical_search_result = Technical.objects.filter().distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter().distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter IssuedBy
            if ib and not sp and not dt and not oz:
                technical_search_result = Technical.objects.filter(
                    IssuedBy__icontains=ib).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    IssuedBy__icontains=ib).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter IssuedBy & phrase
            if ib and sp and not dt and not oz:
                technical_search_result = Technical.objects.filter(
                    technical_lookup, IssuedBy__icontains=ib).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup, IssuedBy__icontains=ib).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter IssuedBy,phrase & doctype
            if ib and sp and dt and not oz:
                technical_search_result = Technical.objects.filter(
                    technical_lookup, IssuedBy__icontains=ib, Category__icontains=dt).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup, IssuedBy__icontains=ib, Category__icontains=dt).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter phrase & organization
            if not ib and sp and not dt and oz:
                technical_search_result = Technical.objects.filter(
                    technical_lookup, Company__icontains=oz).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup, Office__icontains=oz).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter IssuedBy,phrase & doctype
            if ib and not sp and dt and not oz:
                technical_search_result = Technical.objects.filter(
                    IssuedBy__icontains=ib, Category__icontains=dt).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    IssuedBy__icontains=ib, Category__icontains=dt).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter phrase
            if not ib and sp and not dt and not oz:
                technical_search_result = Technical.objects.filter(
                    technical_lookup).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter doctype
            if not ib and not sp and dt and not oz:
                technical_search_result = Technical.objects.filter(
                    Category__icontains=dt).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    Category__icontains=dt).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter phrase & doctype
            if not ib and sp and dt and not oz:
                technical_search_result = Technical.objects.filter(
                    technical_lookup, Category__icontains=dt).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup, Category__icontains=dt).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)

    # BASIC USER
    else:
        if sd and ed:
            # filter all
            if ib and sp and dt:
                technical_search_result = Technical.objects.filter(
                    technical_lookup,
                    CreatedDate__range=[
                        sd,
                        ed],
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup,
                    CreatedDate__range=[
                        sd,
                        ed],
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter phrase, doctype
            if not ib and sp and dt:
                technical_search_result = Technical.objects.filter(
                    technical_lookup, CreatedDate__range=[
                        sd, ed], Category__icontains=dt, Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup, CreatedDate__range=[
                        sd, ed], Category__icontains=dt, Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter doctype & organization
            if not ib and not sp and dt:
                technical_search_result = Technical.objects.filter(
                    Category__icontains=dt, CreatedDate__range=[
                        sd, ed], Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    Category__icontains=dt, CreatedDate__range=[
                        sd, ed], Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter organization
            if not ib and not sp and not dt:
                technical_search_result = Technical.objects.filter(
                    Company__icontains=company, CreatedDate__range=[sd, ed]).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    Office__icontains=company, CreatedDate__range=[sd, ed]).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter none
            if not ib and not sp and not dt:
                technical_search_result = Technical.objects.filter(
                    CreatedDate__range=[sd, ed], Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    CreatedDate__range=[sd, ed], Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter IssuedBy
            if ib and not sp and not dt:
                technical_search_result = Technical.objects.filter(
                    IssuedBy__icontains=ib, CreatedDate__range=[
                        sd, ed], Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    IssuedBy__icontains=ib, CreatedDate__range=[
                        sd, ed], Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter IssuedBy & phrase
            if ib and sp and not dt:
                technical_search_result = Technical.objects.filter(
                    technical_lookup, IssuedBy__icontains=ib, CreatedDate__range=[
                        sd, ed], Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup, IssuedBy__icontains=ib, CreatedDate__range=[
                        sd, ed], Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter IssuedBy,phrase & doctype
            if ib and sp and dt:
                technical_search_result = Technical.objects.filter(
                    technical_lookup,
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    CreatedDate__range=[
                        sd,
                        ed],
                    Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup,
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    CreatedDate__range=[
                        sd,
                        ed],
                    Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter phrase & organization
            if not ib and sp and not dt:
                technical_search_result = Technical.objects.filter(
                    technical_lookup, Company__icontains=company, CreatedDate__range=[
                        sd, ed]).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup, Office__icontains=company, CreatedDate__range=[
                        sd, ed]).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter IssuedBy,phrase & doctype
            if ib and not sp and dt:
                technical_search_result = Technical.objects.filter(
                    IssuedBy__icontains=ib, Category__icontains=dt, CreatedDate__range=[
                        sd, ed], Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    IssuedBy__icontains=ib, Category__icontains=dt, CreatedDate__range=[
                        sd, ed], Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter phrase
            if not ib and sp and not dt:
                technical_search_result = Technical.objects.filter(
                    technical_lookup, CreatedDate__range=[
                        sd, ed], Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup, CreatedDate__range=[
                        sd, ed], Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter dt
            if not ib and not sp and dt:
                technical_search_result = Technical.objects.filter(
                    Category__icontains=dt, CreatedDate__range=[
                        sd, ed], Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    Category__icontains=dt, CreatedDate__range=[
                        sd, ed], Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)

        if sd and not ed:
            # filter all
            if ib and sp and dt:
                technical_search_result = Technical.objects.filter(
                    technical_lookup,
                    CreatedDate__range=[
                        sd,
                        d3],
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup,
                    CreatedDate__range=[
                        sd,
                        d3],
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter phrase, doctype
            if not ib and sp and dt:
                technical_search_result = Technical.objects.filter(
                    technical_lookup, CreatedDate__range=[
                        sd, d3], Category__icontains=dt, Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup, CreatedDate__range=[
                        sd, d3], Category__icontains=dt, Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter none
            if not ib and not sp and not dt:
                technical_search_result = Technical.objects.filter(
                    CreatedDate__range=[sd, d3], Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    CreatedDate__range=[sd, d3], Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter IssuedBy
            if ib and not sp and not dt:
                technical_search_result = Technical.objects.filter(
                    IssuedBy__icontains=ib, CreatedDate__range=[
                        sd, d3], Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    IssuedBy__icontains=ib, CreatedDate__range=[
                        sd, d3], Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter IssuedBy & phrase
            if ib and sp and not dt:
                technical_search_result = Technical.objects.filter(
                    technical_lookup, IssuedBy__icontains=ib, CreatedDate__range=[
                        sd, d3], Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup, IssuedBy__icontains=ib, CreatedDate__range=[
                        sd, d3], Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter IssuedBy,phrase & doctype
            if ib and sp and dt:
                technical_search_result = Technical.objects.filter(
                    technical_lookup,
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    CreatedDate__range=[
                        sd,
                        d3],
                    Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup,
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    CreatedDate__range=[
                        sd,
                        d3],
                    Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)

            # filter IssuedBy & doctype
            if ib and not sp and dt:
                technical_search_result = Technical.objects.filter(
                    IssuedBy__icontains=ib, Category__icontains=dt, CreatedDate__range=[
                        sd, d3], Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    IssuedBy__icontains=ib, Category__icontains=dt, CreatedDate__range=[
                        sd, d3], Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter phrase
            if not ib and sp and not dt:
                technical_search_result = Technical.objects.filter(
                    technical_lookup, CreatedDate__range=[
                        sd, d3], Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup, CreatedDate__range=[
                        sd, d3], Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter doctype
            if not ib and not sp and dt:
                technical_search_result = Technical.objects.filter(
                    Category__icontains=dt, CreatedDate__range=[
                        sd, d3], Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    Category__icontains=dt, CreatedDate__range=[
                        sd, d3], Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)

        else:
            # filter all
            if ib and sp and dt:
                technical_search_result = Technical.objects.filter(
                    technical_lookup,
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup,
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter phrase, doctype
            if not ib and sp and dt:
                technical_search_result = Technical.objects.filter(
                    technical_lookup, Category__icontains=dt, Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup, Category__icontains=dt, Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter none
            if not ib and not sp and not dt:
                technical_search_result = Technical.objects.filter(
                    Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter IssuedBy
            if ib and not sp and not dt:
                technical_search_result = Technical.objects.filter(
                    IssuedBy__icontains=ib, Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    IssuedBy__icontains=ib, Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter IssuedBy & phrase
            if ib and sp and not dt:
                technical_search_result = Technical.objects.filter(
                    technical_lookup, IssuedBy__icontains=ib, Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup, IssuedBy__icontains=ib, Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter IssuedBy,phrase & doctype
            if ib and sp and dt:
                technical_search_result = Technical.objects.filter(
                    technical_lookup,
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup,
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter IssuedBy & doctype
            if ib and not sp and dt:
                technical_search_result = Technical.objects.filter(
                    IssuedBy__icontains=ib,
                    Category__icontains=dt,
                    Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    IssuedBy__icontains=ib, Category__icontains=dt, Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter phrase
            if not ib and sp and not dt:
                technical_search_result = Technical.objects.filter(
                    technical_lookup, Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    mappedtechnical_lookup, Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)
            # filter doctype
            if not ib and not sp and dt:
                technical_search_result = Technical.objects.filter(
                    Category__icontains=dt, Company__icontains=company).distinct().order_by('-id')
                mappedtechnical_search_result = MappedTechnical.objects.filter(
                    Category__icontains=dt, Office__icontains=company).distinct().order_by('-id')
                if classname:
                    if classname == 'All':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                        }
                    elif classname == 'Non-Paired':
                        context = {
                            'startdate': sd,
                            'enddate': enddate,
                            'preparedby': ib,
                            'classname': classname,
                            'preparedbylist': preparedbylist,
                            'organization': oz,
                            'doctype': dt,
                            'search': search,
                            'mailer': mailer,
                            'technical_advancedsearch_result': technical_search_result,
                        }
                else:
                    context = {
                        'startdate': sd,
                        'enddate': enddate,
                        'preparedby': ib,
                        'preparedbylist': preparedbylist,
                        'organization': oz,
                        'doctype': dt,
                        'search': search,
                        'mailer': mailer,
                        'technical_advancedsearch_result': technical_search_result,
                        'mappedtechnical_advancedsearch_result': mappedtechnical_search_result,
                    }
                if technical_search_result or mappedtechnical_search_result:
                    return render(request, 'advancedsearch.html', context)
                messages.info(
                    request, "no results found for unfiltered search!")
                return render(request, 'advancedsearch.html', context)

    context = {
        'search': search,
        'preparedbylist': preparedbylist,
        'mailer': mailer,
    }

    return render(request, 'advancedsearch.html')




def technicalmailupdate(request, pk):
    user = request.user
    record=Technical.objects.filter(pk=pk)
    for i in record:
        receipt_number=i.ReceiptNumber
    mailer = True
    emails_list = request.POST['receivermail']
    check_list=emails_list.split(';')
    new_list=[]
    email_string=''
    new_email_string=''
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
 
    if emails_list:
        placeholder=emails_list
    else:
        placeholder='Receiver Email'

    for i in check_list:
        if ( re.fullmatch(email_pattern, i) ):
            new_list.append(i)
        else:
            error= f"Invalid email: '{i}' " 
            context = {
                'mailer': mailer,
                'placeholder':placeholder,
                'receipt_number':receipt_number,
                'sendtechnical': record,
            }
            messages.error(request, f"{error}")
            # return render(request, 'mailer/mailer.html', context)
            return False

    for x in new_list:
        email_string += ';'+ x
        new_email_string=email_string.lstrip(email_string[0])
     
    if new_email_string == emails_list:
       
        record.update(ReceiverEmail=new_email_string)
       

        for i in record:
            # Register page activity
            user = request.user
            page_activity=f"updated receiver email on #{i.ReceiptNumber}"
            custom_receiver(user,request,page_activity)
        return True
    else:
        messages.error(request, f"something went wrong, please try again!")
        return False



def mappedtechnicalmailupdate(request,pk):
    record=MappedTechnical.objects.filter(pk=pk)
    for i in record:
        receipt_number=i.ReceiptNumber
    mailer = True
    emails_list = request.POST['receivermail']
    check_list=emails_list.split(';')
    new_list=[]
    email_string=''
    new_email_string=''
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
 
    if emails_list:
        placeholder=emails_list
    else:
        placeholder='Receiver Email'

    for i in check_list:
        if ( re.fullmatch(email_pattern, i) ):
            new_list.append(i)
        else:
            error= f"Invalid email: '{i}' " 
            context = {
                'mailer': mailer,
                'placeholder':placeholder,
                'receipt_number':receipt_number,
                'sendmappedtechnical': record,
            }
            messages.error(request, f"{error}")
            # return render(request, 'preview.html', context)
            return redirect('PreviewApp:preview', foo=receipt_number)

    for x in new_list:
        email_string += ';'+ x
        new_email_string=email_string.lstrip(email_string[0])
    
        
    if new_email_string == emails_list:
      
        MappedTechnical.objects.filter(pk=pk).update(ReceiverEmail=new_email_string)

       
        query_updated_record=MappedTechnical.objects.filter(pk=pk)
        
        for i in query_updated_record:
            # Register page activity
            user = request.user
            page_activity=f"updated receiver email on #{i.ReceiptNumber}"
            custom_receiver(user,request,page_activity)        
        return True
    else:
        messages.error(request, f"something went wrong, please try again!")
        return False


@login_required(login_url='account:login')
def updatepaymentadvise(request, foo, pk):
    user=request.user
    mappedtechnical = MappedTechnical.objects.filter(
        ReceiptNumber__icontains=foo)

    filename = foo + ".pdf"
    filepath = os.path.join(settings.FILES_DIR, filename)

    rate = 0
    currency_type = request.POST.get('currency')
    conversion = request.POST.get('rate')
    purpose = request.POST.get('purpose')
    doclanguage = request.POST.get('doclanguage')


    context = {
        'filepath': filepath,
        'purpose': purpose,
        'doclanguage': doclanguage,
        'mappedtechnical': mappedtechnical,
        'receipt_number': foo,
        'currency': currency_type,
        'new': rate
    }
    for i in mappedtechnical:
        if currency_type == i.Currency:
            messages.error(request, f"Selected currency '{currency_type}' already applied" )
            # return render(request, 'edit_pa.html', context)
            return redirect('PreviewApp:preview', foo=foo)

    if currency_type and not conversion:
        messages.error(request, "Please provide a conversion rate for the selected currency" )
        # return render(request, 'edit_pa.html', context)
        return redirect('PreviewApp:preview', foo=foo)
    if conversion:
        rate = float(conversion)
    rate = conversion
    update_fields={}

    if request.method == 'POST':
        receivermail = request.POST.get('receivermail')

        if currency_type:
            update_fields['Currency'] = currency_type
        if purpose:
            update_fields['Purpose'] = purpose
        if doclanguage:
            update_fields['Doclanguage'] = doclanguage

        if update_fields:
            response = updatepaymentadvice(foo, rate, currency_type, purpose, doclanguage,user,request)
          
            if response.status_code == 200:
                keys= list(update_fields.keys())
                messages.success(request, f"{keys} updated successfully")
                mappedtechnical.update(**update_fields)
            else:
                messages.error(request, f"Error - {response.status_code}")
        if receivermail:
            response=mappedtechnicalmailupdate(request, pk)
            if response:
                messages.success(request, "Receiver email updated successfully")
    return redirect('PreviewApp:preview', foo=foo)


@login_required(login_url='account:login')
def updateremmittance_allocation(request, foo,pk):
    user=request.user
    mappedtechnical = MappedTechnical.objects.filter(ReceiptNumber__icontains=foo)
    filename = foo + ".pdf"
    filepath = os.path.join(settings.FILES_DIR, filename)
    doclanguage = request.POST.get('doclanguage')
    update_fields={}
    context = {
        'filepath': filepath,
        'doclanguage': doclanguage,
        'mappedtechnical': mappedtechnical,
        'receipt_number': foo,

    }
    if request.method == 'POST':
        receivermail = request.POST.get('receivermail')

        if doclanguage:
            update_fields['Doclanguage'] = doclanguage
        if update_fields:
            response = updateremittanceallocation(foo, doclanguage,user,request)
           
            if response.status_code == 200:
                keys= list(update_fields.keys())
                messages.success(request, f"{keys} updated successfully")
                mappedtechnical.update(**update_fields)
            else:
                messages.error(request, f"Error - {response.status_code}")
        if receivermail:
            response=mappedtechnicalmailupdate(request, pk)
            if response:
                messages.success(request, "Receiver email updated successfully")
        
    return redirect('PreviewApp:preview', foo=foo)



def updatenonpaired_receipt(request, foo,pk):
    user = request.user
    technical = Technical.objects.filter(ReceiptNumber__icontains=foo)
    filename = foo + ".pdf"
    filepath = os.path.join(settings.FILES_DIR, filename)
    context = {
        'filepath': filepath,
        'technical': technical,
        'receipt_number': foo,
    }

    if request.method == 'POST':
        doclanguage = request.POST.get('doclanguage')
        narration = request.POST.get('narration')
        receivermail = request.POST.get('receivermail')
        destinationbank = request.POST.get('destinationbank')

        update_fields = {}
        if doclanguage:
            update_fields['Doclanguage'] = doclanguage
        if narration:
            update_fields['Narration'] = narration
        
        if destinationbank:
            update_fields['BankName'] = destinationbank

        if update_fields:
            response = updatenonpairedreceipt(foo, doclanguage,narration,destinationbank,user,request)
            if response.status_code == 200:
                keys= list(update_fields.keys())
                messages.success(request, f"{keys} updated successfully")
                technical.update(**update_fields)
            else:
                messages.error(request, f"Error - {response.status_code}")

        if receivermail:
            response=technicalmailupdate(request, pk)
            if response:
                messages.success(request, "Receiver email updated successfully")
    return redirect('PreviewApp:preview', foo=foo)


@login_required(login_url='account:login')
def pdf_view(request, foo):
    fs = FileSystemStorage()
    filename = f'{foo}.pdf'
    if fs.exists(filename):
        with fs.open(filename) as pdf:
            response = HttpResponse(pdf, content_type='application/pdf')
            # response['Content-Disposition']='attachment;filename="my.pdf"'
            response['Content-Disposition'] = f'inline;filename="{filename}"'
            return response
    else:
        return HttpResponseNotFound('File not found')


def handler404(request, exception):
    return render(request, 'error/404.html')


def handler500(request, exception):
    return render(request, 'error/505.html')
