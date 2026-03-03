from django.db import models
from accounts.models import User,Company
# Create your models here.

class OtherSignersTable(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, db_column='id')
    fileName= models.CharField(max_length=500, db_column='fileName')
    fileguid= models.CharField(max_length=500, db_column='fileguid')
    Email= models.CharField(max_length=500, db_column='Email')
    senderEmail= models.CharField(max_length=500, db_column='senderEmail')
    IsSigned=models.BooleanField(db_column='IsSigned')
    IsCurrent=models.BooleanField(db_column='IsCurrent')
    senderName= models.CharField(max_length=500, db_column='senderName')

    class Meta:
        db_table='OtherSignersTable'

    def __str__(self):
        return self.fileguid
    
class Document(models.Model):
   
    guid=models.CharField(max_length=400,primary_key=True,db_column='docGuid')
    trashed=models.BooleanField(db_column='Trashed')
    title=models.CharField(max_length=400,db_column='title')
    declinedby=models.CharField(max_length=400,db_column='DeclinedBy')
    docdate=models.DateTimeField(db_column='docDate',blank=True,null=True)
    signedcomplete=models.BooleanField(default=False,db_column='SignedComplete',blank=True,null=True)
    declined=models.BooleanField(default=False,db_column='Declined',blank=True,null=True)
    selfsign=models.BooleanField(default=False,db_column='SelfSign',blank=True,null=True)
    signeddate=models.DateTimeField(db_column='SignedCompletedDate',blank=True,null=True)
    userid=models.ForeignKey(User,on_delete=models.CASCADE,db_column='userid')
    assignmentd=models.CharField(max_length=400,db_column='assignmentd',blank=True,null=True)
    VaultGuid=models.CharField(max_length=400,db_column='VaultGuid',blank=True,null=True)
    documentpages=models.CharField(max_length=400,db_column='documentpages',blank=True,null=True)
    MfilesDocsGuid=models.CharField(max_length=400,db_column='MfilesDocsGuid',blank=True,null=True)
    RequesterName=models.CharField(max_length=400,db_column='RequesterName',blank=True,null=True)
    RequesterEmail=models.CharField(max_length=400,db_column='RequesterEmail',blank=True,null=True)
    trashed=models.BooleanField(default=False,db_column='Trashed',blank=True,null=True)
    expirydate=models.DateTimeField(db_column='ExpiryDate',blank=True,null=True)
    

    @property
    def signers(self):
        queryset = Signer.objects.filter(document=self)
        return [
            {
                'uid': s.uid,
                'email': s.email,
                'signed': str(s.signed),
                'signed_time_stamp': s.signed_timestamp,
                'current_signer': str(s.current_signer),
                'document': s.document.guid,
                'declinedby': s.document.declinedby,
                'otp': s.isOtpVerify,
                'otpnumber': s.phone,
            }
            if s.isOtpVerify else
            {
                'uid': s.uid,
                'email': s.email,
                'signed': str(s.signed),
                'signed_time_stamp': s.signed_timestamp,
                'current_signer': str(s.current_signer),
                'document': s.document.guid,
                'declinedby': s.document.declinedby,
            }
            for s in queryset
        ]

    @property
    def signersStatus(self):
        queryset = Signer.objects.filter(document=self)
        return [
            {
                'email': s.email,
                'signed': str(s.signed),
                'signed_time_stamp': s.signed_timestamp,
                'current_signer': str(s.current_signer),
            }
            for s in queryset
        ]

    @property
    def signers_emails(self):
        return Signer.objects.filter(document=self).values_list('email', flat=True)

    @property
    def getSignerDeclined(self):
        signer = Signer.objects.get(uid=self.declinedby)
        return signer.email

    @property
    def getSignerCurrent(self):
        return Signer.objects.filter(document=self, current_signer=True).values_list('email', flat=True).first()

    @property
    def getCompanyName(self):
        return self.userid.company.name

    class Meta:
        db_table='documents'
  
        ordering = ('docdate',)

    def __unicode__(self):
        return self.guid

class Signer(models.Model):
    uid=models.CharField(max_length=400,primary_key=True,db_column='uid')
    email=models.CharField(max_length=400,db_column='email')
    phone=models.CharField(max_length=400,db_column='phone',blank=True,null=True)
    current_signer=models.BooleanField(default=False,db_column='currentsigner',blank=True,null=True)
    signed=models.BooleanField(default=False,db_column='Signed',blank=True,null=True)
    name=models.CharField(max_length=400,db_column='name',blank=True,null=True)
    senttime=models.CharField(max_length=400,db_column='senttime',blank=True,null=True)
    signed_timestamp=models.DateTimeField(db_column='Signedtimestamp',blank=True,null=True) 
    ip_address=models.CharField(max_length=400,db_column='ipaddress',blank=True,null=True)
    document=models.ForeignKey(Document,on_delete=models.CASCADE,db_column='documentid')
    isOtpVerify=models.BooleanField(default=False,db_column='isOtpVerify',blank=True,null=True)
    viewtime=models.BooleanField(default=False,db_column='viewtime',blank=True,null=True)
    authenticate_signer = models.BooleanField(db_column='Authenticate',blank=True,null=True)
    trashed=models.BooleanField(default=False,db_column='Trashed',blank=True,null=True)

    @property
    def getSignersComments(self):
        signers_comments=Comment.objects.filter(signer=self.uid)
        return signers_comments

    class Meta:
        db_table='signers'

    def _str_(self):
        return self.uid

class SignerAnnotation(models.Model):
    # Foreign key linking to the Signer model
    signer = models.ForeignKey(Signer, on_delete=models.CASCADE, db_column='signer_id', related_name='signers_annotations')

    # Annotation-specific fields
    id = models.BigIntegerField(db_column='id', unique=True,primary_key=True)  # Matches the "id" in annotations
    page_number = models.IntegerField(db_column='page_number')  # Matches "pageNumber"
    x = models.FloatField(db_column='x')  # Matches "x"
    y = models.FloatField(db_column='y')  # Matches "y"
    width = models.FloatField(db_column='width')  # Matches "width"
    height = models.FloatField(db_column='height')  # Matches "height"
    text = models.TextField(db_column='text', blank=True, null=True)  # Slightly refined "text"
    color = models.CharField(max_length=50, db_column='color', blank=True, null=True)  # Slightly refined "color"

    class Meta:
        db_table = 'signers_annotations'  # Singular form for clarity

    def __str__(self):
        return f"Annotation {self.annotation_id} for Signer {self.signer.uid}"
    
class SMTPConfigs(models.Model):
    port= models.IntegerField(db_column='SMTPPort',blank=True,null=True)
    url= models.CharField(max_length=400,db_column='SMTPurl',blank=True,null=True)
    username= models.CharField(max_length=400,db_column='SMTPUsername',blank=True,null=True)
    password= models.CharField(max_length=400,db_column='SMTPPassword',blank=True,null=True)
    user= models.ForeignKey(User,on_delete=models.CASCADE,db_column='UserId',blank=True,null=True)
    company= models.ForeignKey(Company,on_delete=models.CASCADE,db_column='CompanyId',blank=True,null=True)
    display_name= models.CharField(max_length=400,db_column='DisplayName',blank=True,null=True)

    class Meta:
        db_table='SMTPCredsTables'

    def _str_(self):
        return self.display_name

class Logger(models.Model):
    activity=models.CharField(max_length=400,db_column='activity')
    guid=models.CharField(max_length=400,db_column='guid',blank=True,null=True)
    description=models.CharField(max_length=400,db_column='description',blank=True,null=True)
    ip=models.CharField(max_length=400,db_column='ip',blank=True,null=True)
    created_date=models.DateTimeField(db_column='created_date',auto_now_add=True)
    user=models.CharField(max_length=400,db_column='user',blank=True,null=True)

    @property
    def getotpphone(self):
        try: 
            document= Document.objects.get(guid=self.guid)
            signer=Signer.objects.get(document=document,email=self.user)
            return signer.phone
        except:
            return ""
  
 
    class Meta:
       db_table='Logger'

       

    def __str__(self):
        return f'({self.user} - {self.created_date} - {self.activity}'

class Comment(models.Model):
    comment=models.CharField(max_length=500,blank=True,null=True,db_column='comment')
    signer=models.ForeignKey(Signer,on_delete=models.CASCADE,db_column='signer')
    posted=models.DateTimeField(auto_now_add=True,db_column='posted')

    class Meta:
        db_table='comments'

        ordering = ('posted',)
  
