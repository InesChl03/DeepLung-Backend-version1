# from rest_framework import serializers
# from .models import CtScan, Nodule


# class NoduleSerializer(serializers.ModelSerializer):
#     class Meta:
#         model  = Nodule
#         fields = [
#             'id', 'rang',
#             'monde_z', 'monde_y', 'monde_x',
#             'voxel_z', 'voxel_y', 'voxel_x',
#             'diametre_mm', 'probabilite',
#             'created_at',
#         ]


# class CtScanListSerializer(serializers.ModelSerializer):
#     nb_nodules = serializers.SerializerMethodField()
#     patient    = serializers.SerializerMethodField()

#     class Meta:
#         model  = CtScan
#         fields = ['id', 'statut', 'nb_nodules', 'patient', 'duree_analyse', 'created_at', 'updated_at']

#     def get_nb_nodules(self, obj):
#         return obj.nodules.count()

#     def get_patient(self, obj):
#         p = obj.dossier.patient
#         return {'id': p.id, 'nom': p.nom, 'prenom': p.prenom}


# class CtScanDetailSerializer(serializers.ModelSerializer):
#     nodules    = NoduleSerializer(many=True, read_only=True)
#     nb_nodules = serializers.SerializerMethodField()
#     patient    = serializers.SerializerMethodField()
#     origin     = serializers.SerializerMethodField()
#     spacing    = serializers.SerializerMethodField()
#     ebox       = serializers.SerializerMethodField()

#     class Meta:
#         model  = CtScan
#         fields = [
#             'id', 'dossier', 'statut',
#             'fichier_mhd', 'fichier_raw',
#             'origin', 'spacing', 'ebox',
#             'message_erreur', 'duree_analyse',
#             'nb_nodules', 'nodules',
#             'patient', 'created_at', 'updated_at',
#         ]
#     def get_ebox(self, obj):                           # ← ajouter
#         if obj.ebox_z is None:
#             return None
#         return [obj.ebox_z, obj.ebox_y, obj.ebox_x]
#     def get_nb_nodules(self, obj):
#         return obj.nodules.count()

#     def get_patient(self, obj):
#         p = obj.dossier.patient
#         return {'id': p.id, 'nom': p.nom, 'prenom': p.prenom, 'age': p.age, 'sexe': p.sexe}

#     def get_origin(self, obj):
#         if obj.origin_z is None:
#             return None
#         return [obj.origin_z, obj.origin_y, obj.origin_x]

#     def get_spacing(self, obj):
#         if obj.spacing_z is None:
#             return None
#         return [obj.spacing_z, obj.spacing_y, obj.spacing_x]


# class CtScanUploadSerializer(serializers.Serializer):
#     dossier_id  = serializers.IntegerField()
#     fichier_mhd = serializers.FileField()
#     fichier_raw = serializers.FileField()
    
    
    
# class CtScanDicomUploadSerializer(serializers.Serializer):
#     dossier_id  = serializers.IntegerField()
#     fichier_zip = serializers.FileField()  # dossier DICOM zippé
# class CtScanAnalyserDicomView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         serializer = CtScanDicomUploadSerializer(data={
#             'dossier_id':  request.data.get('dossier_id'),
#             'fichier_zip': request.FILES.get('fichier_zip'),
#         })

#         if not serializer.is_valid():
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#         data = serializer.validated_data

#         try:
#             _check_file_size(data['fichier_zip'], 'fichier_zip')
#         except ValueError as e:
#             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

#         dossier = get_object_or_404(
#             Dossier,
#             id=data['dossier_id'],
#             patient__doctor__user=request.user,
#         )

#         ctscan = CtScan.objects.create(
#             dossier = dossier,
#             statut  = CtScan.Statut.EN_COURS,
#         )
#         logger.info(f"[CtScan #{ctscan.id}] Analyse DICOM lancée")

#         tmp_dir = tempfile.mkdtemp(prefix='dicom_upload_')

#         try:
#             # ── 1. Écrire et extraire le zip ─────────────────────────────────
#             zip_path = os.path.join(tmp_dir, 'upload.zip')
#             data['fichier_zip'].seek(0)
#             with open(zip_path, 'wb') as f:
#                 for chunk in data['fichier_zip'].chunks():
#                     f.write(chunk)

#             dicom_dir = os.path.join(tmp_dir, 'dicom')
#             os.makedirs(dicom_dir)
#             with zipfile.ZipFile(zip_path, 'r') as z:
#                 z.extractall(dicom_dir)

#             # ── 2. Trouver le dossier contenant les .dcm ─────────────────────
#             dcm_folder = _find_dicom_folder(dicom_dir)

#             # ── 3. Conversion DICOM → .mhd + .raw ───────────────────────────
#             mhd_dir = os.path.join(tmp_dir, 'mhd')
#             os.makedirs(mhd_dir)
#             mhd_path, raw_path = convert_dicom_to_mhd(
#                 dicom_folder = dcm_folder,
#                 output_dir   = mhd_dir,
#                 output_name  = "scan",
#             )

#             # ── 4. Pipeline TiCNet ────────────────────────────────────────────
#             resultat = analyser_ctscan(mhd_path, raw_path)

#             # ── 5. Appliquer les métadonnées sur l'instance ──────────────────
#             _apply_resultat_to_ctscan(ctscan, resultat)

#             # ── 6. Sauvegarder les fichiers + persister les chemins en base ──
#             _save_scan_files(ctscan, mhd_path, raw_path)

#             # ── 7. Sauvegarder les métadonnées (fichier_mhd/raw déjà en base)─
#             ctscan.save()
#             ctscan.refresh_from_db()

#             # ── 8. Créer les Nodules ──────────────────────────────────────────
#             nodules_db = _create_nodules(ctscan, resultat['nodules'])

#             logger.info(
#                 f"[CtScan #{ctscan.id}] ✅ DICOM terminé — "
#                 f"{len(nodules_db)} nodules en {resultat['duree']}s"
#             )

#             # ── 9. Classification ResNet50-SWS (automatique, non bloquante) ──
#             if nodules_db:
#                 try:
#                     classify_scan(ctscan)
#                     logger.info(f"[CtScan #{ctscan.id}] ✅ Classification terminée")
#                 except Exception as e:
#                     logger.error(
#                         f"[CtScan #{ctscan.id}] ⚠️ Classification échouée "
#                         f"(scan reste TERMINE) : {e}"
#                     )

#             return Response(
#                 CtScanDetailSerializer(ctscan).data,
#                 status=status.HTTP_201_CREATED,
#             )

#         except Exception as e:
#             logger.exception(f"[CtScan #{ctscan.id}] ❌ Erreur DICOM")
#             ctscan.statut         = CtScan.Statut.ERREUR
#             ctscan.message_erreur = str(e)
#             ctscan.save(update_fields=['statut', 'message_erreur'])
#             return Response(
#                 {
#                     "error":     "Erreur conversion DICOM",
#                     "detail":    str(e),
#                     "ctscan_id": ctscan.id,
#                 },
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )

#         finally:
#             shutil.rmtree(tmp_dir, ignore_errors=True)


# # ── GET /api/ctscan/<id>/slice/<z>/ ──────────────────────────────────────────
# class CtScanSliceView(APIView):
#     permission_classes = [IsAuthenticated]
#     WINDOWS = {
#         'pulmonaire': (-1500,  500),
#         'nodule':     (-800,   800),
#         'mediastin':  (-175,   275),
#         'standard':   (-600,  1600),
#         'os':         (-500,  1500),
#     }

#     def get(self, request, pk, z):
#         ctscan = get_object_or_404(
#             CtScan,
#             pk=pk,
#             dossier__patient__doctor__user=request.user,
#         )

#         if not ctscan.fichier_mhd or not ctscan.fichier_mhd.name:
#             return Response(
#                 {"error": "fichier_mhd absent pour ce scan"},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         mhd_path = ctscan.fichier_mhd.path
#         if not os.path.isfile(mhd_path):
#             return Response(
#                 {"error": f"fichier .mhd introuvable : {mhd_path}"},
#                 status=status.HTTP_404_NOT_FOUND,
#             )

#         z_preprocessed    = int(z)
#         ebox_z            = float(ctscan.ebox_z)    if ctscan.ebox_z    is not None else 0.0
#         spacing_z         = float(ctscan.spacing_z) if ctscan.spacing_z is not None else 1.0
#         SPACING_RESAMPLED = 1.0

#         z_original = int((z_preprocessed + ebox_z) * (SPACING_RESAMPLED / spacing_z))

#         logger.info(
#             f"[SliceView] voxel_z préprocessé={z_preprocessed} "
#             f"ebox_z={ebox_z} spacing_z={spacing_z} "
#             f"→ z_original={z_original}"
#         )

#         try:
#             image  = sitk.ReadImage(mhd_path)
#             volume = sitk.GetArrayFromImage(image)  # (D, H, W)
#         except Exception as e:
#             logger.exception(f"[CtScan #{ctscan.id}] Erreur lecture .mhd")
#             return Response(
#                 {"error": f"Erreur lecture .mhd : {str(e)}"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )

#         view = request.GET.get('view', 'axial')

#         axis_map = {
#             'axial':    (0, lambda v, i: v[i]),
#             'coronal':  (1, lambda v, i: v[:, i, :]),
#             'sagittal': (2, lambda v, i: v[:, :, i]),
#         }

#         if view not in axis_map:
#             return Response(
#                 {"error": "view invalide (axial|coronal|sagittal)"},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         axis, extractor = axis_map[view]
#         total           = volume.shape[axis]

#         if not (0 <= z_original < total):
#             return Response(
#                 {
#                     "error":  f"Index converti {z_original} hors limites (0–{total-1})",
#                     "detail": f"voxel_z={z_preprocessed} ebox_z={ebox_z} spacing_z={spacing_z}",
#                 },
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         slice_arr = extractor(volume, z_original)

#         # ── Fenêtrage dynamique + encodage PNG ────────────────────────────────
#         window              = request.GET.get('window', 'nodule')
#         win_min, win_max    = self.WINDOWS.get(window, (-800, 800))
#         win_range           = win_max - win_min

#         slice_arr = np.clip(slice_arr, win_min, win_max)
#         slice_arr = ((slice_arr - win_min) / win_range * 255).astype(np.uint8)

#         img = Image.fromarray(slice_arr).convert("RGB")
#         buf = io.BytesIO()
#         img.save(buf, format="PNG")
#         b64 = base64.b64encode(buf.getvalue()).decode()

#         return Response({
#             "slice_index":        z_original,
#             "slice_preprocessed": z_preprocessed,
#             "total_slices":       total,
#             "width":              slice_arr.shape[1],
#             "height":             slice_arr.shape[0],
#             "view":               view,
#             "window":             window,
#             "image_b64":          b64,
#         })
from rest_framework import serializers
from .models import CtScan, Nodule


class NoduleSerializer(serializers.ModelSerializer):
    classification = serializers.SerializerMethodField()

    class Meta:
        model  = Nodule
        fields = [
            'id', 'rang',
            'monde_z', 'monde_y', 'monde_x',
            'voxel_z', 'voxel_y', 'voxel_x',
            'diametre_mm', 'probabilite',
            'created_at',
            'classification',          # ← ajouté
        ]

    def get_classification(self, obj):
        """
        Résultat ResNet50-SWS pour ce nodule, s'il existe.
        Retourne None si la classification n'a pas encore eu lieu
        ou a échoué (le scan reste TERMINE dans ce cas — voir
        ctscan/views.py où classify_scan() est appelé en non-bloquant).
        """
        from classification.models import NoduleClassification
        try:
            clf = NoduleClassification.objects.get(
                scan=obj.ctscan,
                nodule_id_ticnet=obj.id,
            )
        except NoduleClassification.DoesNotExist:
            return None

        return {
            "label":         clf.label,
            "label_str":     "Maligne" if clf.label == 1 else "Benigne",
            "proba_maligne": clf.proba_maligne,
            "proba_benigne": clf.proba_benigne,
        }


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
    ebox       = serializers.SerializerMethodField()

    class Meta:
        model  = CtScan
        fields = [
            'id', 'dossier', 'statut',
            'fichier_mhd', 'fichier_raw',
            'origin', 'spacing', 'ebox',
            'message_erreur', 'duree_analyse',
            'nb_nodules', 'nodules',
            'patient', 'created_at', 'updated_at',
        ]

    def get_ebox(self, obj):
        if obj.ebox_z is None:
            return None
        return [obj.ebox_z, obj.ebox_y, obj.ebox_x]

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


class CtScanDicomUploadSerializer(serializers.Serializer):
    dossier_id  = serializers.IntegerField()
    fichier_zip = serializers.FileField()  # dossier DICOM zippé