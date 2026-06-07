from rest_framework import serializers
from .models import CtScan, Nodule


class NoduleSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Nodule
        fields = [
            'id', 'rang',
            'monde_z', 'monde_y', 'monde_x',
            'voxel_z', 'voxel_y', 'voxel_x',
            'diametre_mm', 'probabilite',
            'created_at',
        ]


class CtScanListSerializer(serializers.ModelSerializer):
    nb_nodules = serializers.SerializerMethodField()
    patient    = serializers.SerializerMethodField()

    class Meta:
        model  = CtScan
        fields = ['id', 'statut', 'nb_nodules', 'patient', 'duree_analyse', 'created_at', 'updated_at']

    def get_nb_nodules(self, obj):
        return obj.nodules.count()

    def get_patient(self, obj):
        p = obj.dossier.patient
        return {'id': p.id, 'nom': p.nom, 'prenom': p.prenom}


class CtScanDetailSerializer(serializers.ModelSerializer):
    nodules    = NoduleSerializer(many=True, read_only=True)
    nb_nodules = serializers.SerializerMethodField()
    patient    = serializers.SerializerMethodField()
    origin     = serializers.SerializerMethodField()
    spacing    = serializers.SerializerMethodField()

    class Meta:
        model  = CtScan
        fields = [
            'id', 'dossier', 'statut',
            'fichier_mhd', 'fichier_raw',
            'origin', 'spacing',
            'message_erreur', 'duree_analyse',
            'nb_nodules', 'nodules',
            'patient', 'created_at', 'updated_at',
        ]

    def get_nb_nodules(self, obj):
        return obj.nodules.count()

    def get_patient(self, obj):
        p = obj.dossier.patient
        return {'id': p.id, 'nom': p.nom, 'prenom': p.prenom, 'age': p.age, 'sexe': p.sexe}

    def get_origin(self, obj):
        if obj.origin_z is None:
            return None
        return [obj.origin_z, obj.origin_y, obj.origin_x]

    def get_spacing(self, obj):
        if obj.spacing_z is None:
            return None
        return [obj.spacing_z, obj.spacing_y, obj.spacing_x]


class CtScanUploadSerializer(serializers.Serializer):
    dossier_id  = serializers.IntegerField()
    fichier_mhd = serializers.FileField()
    fichier_raw = serializers.FileField()
