from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import FAQCategory, SupportTicket, TicketReply


def faq(request):
    categories = FAQCategory.objects.prefetch_related('faqs').filter(faqs__is_published=True).distinct()
    return render(request, 'support/faq.html', {'categories': categories})


@login_required
def ticket_list(request):
    tickets = request.user.support_tickets.all()
    return render(request, 'support/ticket_list.html', {'tickets': tickets})


@login_required
def ticket_create(request):
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        body = request.POST.get('body', '').strip()
        category = request.POST.get('category', 'other')
        if subject and body:
            ticket = SupportTicket.objects.create(user=request.user, subject=subject, body=body, category=category)
            return redirect('support:ticket_detail', pk=ticket.pk)
    return render(request, 'support/ticket_create.html', {'categories': SupportTicket.CATEGORY_CHOICES})


@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(SupportTicket, pk=pk, user=request.user)
    return render(request, 'support/ticket_detail.html', {'ticket': ticket})


@login_required
@require_POST
def ticket_reply(request, pk):
    ticket = get_object_or_404(SupportTicket, pk=pk, user=request.user)
    body = request.POST.get('body', '').strip()
    if body:
        TicketReply.objects.create(ticket=ticket, author=request.user, body=body)
    return redirect('support:ticket_detail', pk=ticket.pk)
