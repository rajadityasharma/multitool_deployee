from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),  # root URL redirect karega
    path('remove-background/', views.background_remover, name='remove_bg'),
    path('enhance-image/', views.image_enhancer, name='enhance_image'), 
    path('compress-image/', views.image_compressor, name='compress_image'),
    path('image-to-pdf/', views.image_to_pdf, name='image_to_pdf'),
    path('crop-image/', views.image_cropper, name='image_cropper'),
    path('stamp-file/', views.stamp_file, name='stamp_file'),
    # path('dashboard/', views.dashboard, name='dashboard'),
]
