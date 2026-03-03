from rest_framework import serializers

class FileUploadSerializer(serializers.Serializer):
    base64_content = serializers.CharField()
    file_extension = serializers.CharField()
