from django.shortcuts import render

<<<<<<< HEAD

def quote_detail(request):
    return render(request, "quotes/quote_detail.html", {})
=======
# Create your views here.
base_price = 120

base_price += bedrooms * 30
base_price += bathrooms * 20

if property_type == "Office":
    base_price += 150

if property_type == "Commercial Property":
    base_price += 250

if property_type == "End of Lease Property":
    base_price += 300

if window_cleaning:
    base_price += 50

if carpet_shampooing:
    base_price += 100

if grout_cleaning:
    base_price += 75

if upholstery_cleaning:
    base_price += 60

if laundry_service:
    base_price += 60

quote.estimated_price = base_price
quote.save()
>>>>>>> 5815f15 (Initial project commit)
