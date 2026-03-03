from django.urls import path
from . import views
from .views import CentralizedLoginView
from django.contrib.auth import views as auth_views

from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

urlpatterns = [
    #  Authentication & Tokens
    path('token/', CentralizedLoginView.as_view(), name='token_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('password_reset/', views.password_reset_view, name='password_reset'),
    path('password_reset_confirm/', views.password_reset_confirm, name='password_reset_confirm'),
    path('pass/', views.test_pass_reset, name='pass'),

    #  Users
    path("register/", views.AddUserViewSet.as_view({'post': 'create'})),
    path("new/user/<int:adminid>/", views.register_user, name="new_user"),
    path("individual/new/user/", views.register_individual_user, name="individual_new_user"),
    path("users/", views.get_users, name="users"),
    path("individual/users/", views.get_Individual_Users, name="individual-users"),
    path("admin/users/", views.get_users_superadmin, name="admnin-users"),
    path('user/<int:pk>', views.UserView.as_view()),

    #  Companies
    path("company/register/", views.register_company, name="register_company"),
    path('company/<int:pk>', views.CompanyView.as_view()),
    path("companies/", views.get_companies_all_superadmin, name="companies"),
    path("new/companies/", views.get_companies_unapproved_superadmin, name="newcompanies"),
    path("approved/companies/", views.get_companies_approved_superadmin, name="approvedcompanies"),
    path('approve/company/<int:id>', views.approve_company, name='approvecompany'),

    #  Documents
    path('doc/', views.getDoc, name='getDocs'),
    path('doc/logs/', views.get_doc_logs, name='get_doc_logs'),
    path('doc/status/', views.docStatus, name='docStatus'),
    path('doc/status/admin/', views.docStatusAdmin, name='docStatusAdmin'),
    path('trash/document/', views.trash_document, name='trash_document'),
    path('untrash/document/', views.untrash_document, name='untrash_document'),
    path('voided/', views.getVoided, name='voided'),
    path('trashed/', views.getTrashed, name='trashed'),
    path('complete/', views.getComplete, name='complete'),
    path("complete/admin/", views.getComplete_admin, name='getComplete_admin'),
    path('resend/summary/document/', views.resend_doc, name='resend_doc'),
    path('org/doc/counts/', views.getOrganizationDocCounts, name='org_doc_counts'),

    #  Signing & Signers
    path("othersigners/", views.otherSigners, name="othersigners"),
    path("othersignersoncesigned/", views.otherSignersOnceSigned, name="othersignersoncesigned"),
    path('signer/', views.getSigner, name='getsigner'),
    path('signer/selfsign/', views.getSigner2, name='signeruid'),
    path('current/signer/', views.getCurrentSigner, name='getcurrentsigner'),
    path('savedsignatures/', views.getSavedSignatures, name='getSavedSignatures'),
    path('saved/selfsign/', views.selfSignSaved, name='saveselfsign'),
    path('selfsign/closesigning/', views.selfSignCloseSigning, name='getSavedSignatures'),
    path('owner/void/', views.ownerVoid, name='ownervoid'),
    path('resend/mail/signer/', views.resend_to_signer, name='resend_to_signer'),

    #  Comments & Annotations
    path('comments/', views.getComments, name='comments'),
    path("new/comments/", views.addComment, name='newcomments'),
    path("annotate/", views.annotate, name='annotate'),
    path("annotations-by-email-and-document/", views.get_annotations_by_signer_email_and_document, name='annotations_by_email_and_document'),

    #  Workflows
    path('workflows/', views.getWorkflows, name='getWorkflows'),
    path("new/workflow/", views.saveWorflow, name='saveWorflow'),
    path('workflow/<int:workflow_id>/delete/', views.deleteWorkflow, name='delete_Workflow'),
    path("organization/workflows/", views.getOrganizationWorkflows, name='getOrganizationWorkflows'),
    path("organization/workflows/create/", views.createOrganizationWorkflow, name='create_organization_workflow'),
    path("organization/workflows/<int:workflow_id>/update/", views.updateOrganizationWorkflow, name='update_organization_workflow'),
    path("organization/workflow/<int:workflow_id>/delete/", views.deleteOrganizationWorkflow, name='delete_Organization_Workflow'),

    # Inbox / Outbox / Uploads
    path("inbox/", views.getInbox, name='inbox'),
    path("outbox/", views.getOutbox, name='outbox'),
    path("myuploads/", views.getMyUploads, name='my-uploads'),
    path("upload/", views.uploadFile, name="upload"),
    path("upload/multi-file/", views.uploadFileMultifile, name="upload-multi-files"),
    
    path("uploadOthers/", views.uploadFileothers, name="uploadothers"),
    path("uploadOthers/multi-files/", views.uploadFileothersMultifiles, name="uploadothers-multi-files"),

    #  Logs & Activity
    path('logs/', views.user_activity, name='get_logs'),
    path('new/log/', views.log_user_activity, name='new_log'),

    #  Settings & Config
    path('update/smtp/configs/', views.update_or_create_smtp_config, name='update_smtp'),
    path('get/smtp/configs/', views.get_smtp_config, name='get_smtp'),
    path('getmyip/', views.get_client_ip, name='get_client_ip'),

    #  Avatars & Logos
    path('avatar/', views.getAvatar, name='avatar'),
    path('logo/', views.getCompanyLogo, name='companylogo'),
    path('logo2/', views.getCompanyLogo2, name='logo2'),

    #  OTP
    path("sms/otp/", views.send_otp, name='otp'),
    path("verify/otp/", views.verify_otp, name='verify_otp'),

    #  Files (Base64)
    path('base64/<str:file>/', views.PDFFileView.as_view(), name='base64'),
]
