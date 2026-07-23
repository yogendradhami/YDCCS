from django.shortcuts import render


def quote_detail(request):
    return render(request, "quotes/quote_detail.html", {})
