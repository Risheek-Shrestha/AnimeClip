from django.contrib.auth.models import User
from django.db import models


class FAQCategory(models.Model):
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'FAQ Category'
        verbose_name_plural = 'FAQ Categories'
        app_label = 'ananimeclip'

    def __str__(self):
        return self.name


class FAQ(models.Model):
    category = models.ForeignKey(FAQCategory, on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=300)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        app_label = 'ananimeclip'

    def __str__(self):
        return self.question


class SupportTicket(models.Model):
    STATUS_CHOICES = [('open', 'Open'), ('in_progress', 'In Progress'), ('resolved', 'Resolved'), ('closed', 'Closed')]
    CATEGORY_CHOICES = [
        ('billing', 'Billing'),
        ('playback', 'Playback Issue'),
        ('account', 'Account'),
        ('content', 'Content Request'),
        ('bug', 'Bug Report'),
        ('other', 'Other'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_tickets')
    subject = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    body = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        app_label = 'ananimeclip'

    def __str__(self):
        return f'#{self.pk} {self.subject} [{self.status}]'


class TicketReply(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    is_staff_reply = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        app_label = 'ananimeclip'

    def __str__(self):
        return f'Reply to #{self.ticket_id} by {self.author.username}'
