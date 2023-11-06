import datetime as dt
from textwrap import dedent

from django import forms
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from confs.models import Fwd50Account, Fwd50Post
from posts.models import PostSubscription


# Create your views here.
def fwd50(request, date: dt.date | None = None):
    search_query = Q(
        visibility="public",
    )
    order = request.GET.get("order")
    if order not in ("-favourites_count", "-created_at"):
        order = "-favourites_count"

    if date:
        date = date.date()
        search_query &= Q(created_at__gte=date, created_at__lt=date + dt.timedelta(days=1))
    else:
        search_query &= Q()

    try:
        account_id = int(request.GET.get("account"))
    except (ValueError, TypeError):
        account_id = None
    if account_id:
        search_query &= Q(account_id=account_id)

    posts = Fwd50Post.objects.filter(search_query).order_by(order)
    # List of date objects. The first one is the date 2023-09-12 and then one item for every day until the current date
    dates = [
        dt.date(2023, 11, 6),
        dt.date(2023, 11, 7),
        dt.date(2023, 11, 8),
    ]

    users_with_most_posts = Fwd50Account.objects.filter().annotate(count=Count("posts")).order_by("-count")[:10]

    counts = (
        Fwd50Post.objects.filter(
            visibility="public",
            created_at__gte=min(dates),
            created_at__lt=max(dates) + dt.timedelta(days=1),
        )
        .values("created_at__date")
        .annotate(count=Count("id"))
    )
    counts_dict = {c["created_at__date"]: c["count"] for c in counts}

    dates = [
        {
            "value": date,
            "pre_display": f"Day {i+1}",
            "display": date,
            "count": counts_dict.get(date, 0),
        }
        for i, date in enumerate(dates)
        if date <= timezone.now().date()
    ]
    paginator = Paginator(posts, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    stats = Fwd50Post.objects.filter(
        visibility="public",
        # created_at__lte=dt.date(2023, 10, 20),
        # created_at__gte=dt.date(2023, 10, 16),
    ).aggregate(
        total_posts=Count("id"),
        total_favourites=Sum("favourites_count"),
    )
    return render(
        request,
        "fwd50.html",
        {
            "page_title": "Mastodon posts FWD50 | Most Favourited Mastodon Posts about FWD50",
            "page_header": "FWD50",
            "page_subheader": "Nov. 6-8, 2023 | Ottawa and online",
            "page_description": "Most Favourited Mastodon Posts about FWD50",
            "page_image": "og-fwd50.png",
            "posts": page_obj,
            "users_with_most_posts": users_with_most_posts,
            "total_posts": stats["total_posts"],
            "total_favourites": stats["total_favourites"],
            "posts_date": date,
            "dates": dates,
            "account_id": account_id,
            "order": order,
        },
    )


class SubscribeForm(forms.ModelForm):
    framework_or_lang = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = PostSubscription
        fields = ["email", "framework_or_lang"]


def subscribe(request):
    if request.method == "POST":
        form = SubscribeForm(request.POST)
        if form.is_valid():
            form.save()
            send_mail(
                "Fedidevs new subscriber!",
                dedent(
                    f"""
                    New subscriber with email {form.cleaned_data["email"]}.
                    Framework or lang: {form.cleaned_data["framework_or_lang"]}
                """
                ),
                "anze@fedidevs.com",
                ["anze@pecar.me"],
                fail_silently=True,
            )
            return redirect("posts_subscribe_success")
        else:
            return render(request, "subscribe.html", {"form": form})
    return render(
        request,
        "subscribe.html",
        {
            "form": SubscribeForm(),
            "page_title": "Fedidevs Subscribe to Daily Posts",
            "page_header": "FEDIDEVS",
            "page_subheader": "Subscribe to Daily Posts"
            + (" on " + request.POST.get("framework_or_lang") if request.POST.get("framework_or_lang") else ""),
        },
    )