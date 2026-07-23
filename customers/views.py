from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from attendance.models import AttendanceLog
from bookings.models import Booking

# Create your views here.


@login_required
def booking_detail(request, booking_id):

    customer = request.user.customer_profile

    booking = get_object_or_404(Booking, id=booking_id, customer=customer)

    before_photos = booking.job_photos.filter(photo_type="before").order_by(
        "-uploaded_at"
    )

    after_photos = booking.job_photos.filter(photo_type="after").order_by(
        "-uploaded_at"
    )

    attendance = AttendanceLog.objects.filter(booking=booking).first()

    return render(
        request,
        "portal/portal_booking_detail.html",
        {
            "booking": booking,
            "before_photos": before_photos,
            "after_photos": after_photos,
            "attendance": attendance,
        },
    )
