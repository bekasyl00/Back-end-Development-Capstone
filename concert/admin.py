from django.contrib import admin

# Register your models here.
from .models import Concert


@admin.register(Concert)
class ConcertAdmin(admin.ModelAdmin):
    list_display = ("concert_name", "city", "date", "duration")
    search_fields = ("concert_name", "city")
    list_filter = ("date",)
