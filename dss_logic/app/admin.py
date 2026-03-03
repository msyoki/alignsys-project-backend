from django.contrib import admin
from .models import OtherSignersTable,Document,Signer,Comment,Logger,SignerAnnotation

# Register your models here.
class OtherSignersTableAdmin(admin.ModelAdmin):
    list_display =('id','fileguid','fileName','Email','IsSigned', 'senderEmail','senderName')
    search_fields=('id','fileguid','senderEmail')
    list_filter=('Email','IsSigned')
    list_per_page=10

class DocumentTableAdmin(admin.ModelAdmin):
    list_display =('guid','title','docdate','docdate','signeddate','userid')
    search_fields=('guid','title','userid')
    list_filter=('userid','guid')
    list_per_page=10

class SignerTableAdmin(admin.ModelAdmin):
    list_display =('uid','email','phone','current_signer','signed','signed_timestamp','ip_address','document')
    search_fields=('uid','email','current_signer','signed')
    list_filter=('uid','email')
    list_per_page=10


class LoggerTableAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'ip', 'activity', 'created_date')
    search_fields = ('id', 'user', 'ip', 'activity','created_date')
    list_filter = ('ip', 'user', 'activity')
    list_per_page = 10

    def get_queryset(self, request):
        # No select_related needed — no FK fields
        return super().get_queryset(request)


# class LoggerTableAdmin(admin.ModelAdmin):
    # list_display =('id','user','ip')
    # search_fields=('id','user')
    # list_filter=('id','user','ip')
    # list_per_page=10


@admin.register(SignerAnnotation)
class SignerAnnotationAdmin(admin.ModelAdmin):
    list_display = (
        "id", "signer", "page_number", "x", "y", "width", "height", "text", "color"
    )
    list_filter = ("text", "signer")
    search_fields = ("signer__uid", "id", "text")
    ordering = ("-id",)
    readonly_fields = ("id",)

    fieldsets = (
        ("Annotation Details", {
            "fields": ("annotation_id", "signer", "page_number")
        }),
        ("Positioning", {
            "fields": ("x", "y", "width", "height")
        }),
        ("Additional Info", {
            "fields": ("text", "color")
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset by selecting related signer data."""
        return super().get_queryset(request).select_related("signer")

    def __str__(self):
        return f"Annotation {self.id} for Signer {self.signer.uid}"

admin.site.register(OtherSignersTable,OtherSignersTableAdmin)
admin.site.register(Document,DocumentTableAdmin)
admin.site.register(Signer,SignerTableAdmin)
admin.site.register(Comment)
admin.site.register(Logger,LoggerTableAdmin)
