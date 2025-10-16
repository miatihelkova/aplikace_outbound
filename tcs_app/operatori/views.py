from django.http import HttpResponse

def dashboard(request):
    return HttpResponse("Operátoři – funguje")