from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from .models import Message, GroupMessage
from users.models import CustomUser
from courses.models import Course, Enrollment


@login_required
def inbox(request):
    user = request.user
    search_query = request.GET.get('q', '').strip()

    # Get all users who have exchanged messages with current user
    sent_to       = Message.objects.filter(sender=user).values_list('receiver', flat=True)
    received_from = Message.objects.filter(receiver=user).values_list('sender', flat=True)
    contact_ids   = set(list(sent_to) + list(received_from))
    contacts      = CustomUser.objects.filter(id__in=contact_ids).exclude(id=user.id)
    
    if search_query:
        contacts = contacts.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    # Build conversations list
    conversations = []
    for contact in contacts:
        last_msg = Message.objects.filter(
            Q(sender=user, receiver=contact) |
            Q(sender=contact, receiver=user)
        ).last()
        unread_count = Message.objects.filter(
            sender=contact, receiver=user, is_read=False
        ).count()
        conversations.append({
            'contact':      contact,
            'last_message': last_msg,
            'unread_count': unread_count,
        })

    conversations.sort(
        key=lambda x: x['last_message'].timestamp if x['last_message'] else timezone.now(),
        reverse=True
    )

    # Show ALL other users so anyone can start a chat
    available_users = CustomUser.objects.exclude(
        id__in=contact_ids
    ).exclude(id=user.id)
    
    if search_query:
        available_users = available_users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    available_users = available_users.order_by('username')

    return render(request, 'chat/inbox.html', {
        'conversations':   conversations,
        'available_users': available_users,
        'search_query':    search_query,
    })

@login_required
def chat_room(request, user_id):
    other_user = get_object_or_404(CustomUser, id=user_id)

    if other_user == request.user:
        return redirect('inbox')

    # Mark incoming messages as read
    Message.objects.filter(
        sender=other_user, receiver=request.user, is_read=False
    ).update(is_read=True)

    # Get full conversation
    messages = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user,   receiver=request.user)
    ).order_by('timestamp')

    # Build sidebar contacts — ALL users who have chatted + this user
    sent_to       = Message.objects.filter(sender=request.user).values_list('receiver', flat=True)
    received_from = Message.objects.filter(receiver=request.user).values_list('sender', flat=True)
    contact_ids   = set(list(sent_to) + list(received_from))
    contact_ids.add(user_id)  # always include current chat partner

    contacts = CustomUser.objects.filter(
        id__in=contact_ids
    ).exclude(id=request.user.id)

    conversations = []
    for contact in contacts:
        last_msg = Message.objects.filter(
            Q(sender=request.user, receiver=contact) |
            Q(sender=contact, receiver=request.user)
        ).last()
        unread = Message.objects.filter(
            sender=contact, receiver=request.user, is_read=False
        ).count()
        conversations.append({
            'contact':      contact,
            'last_message': last_msg,
            'unread_count': unread,
        })

    conversations.sort(
        key=lambda x: x['last_message'].timestamp if x['last_message'] else timezone.now(),
        reverse=True
    )

    return render(request, 'chat/chat_room.html', {
        'other_user':    other_user,
        'messages':      messages,
        'conversations': conversations,
    })

@login_required
def send_message(request, user_id):
    """Send a message to another user."""
    if request.method == 'POST':
        other_user = get_object_or_404(CustomUser, id=user_id)
        text       = request.POST.get('message', '').strip()
        attachment = request.FILES.get('attachment')
        if text or attachment:
            Message.objects.create(
                sender=request.user,
                receiver=other_user,
                message=text,
                attachment=attachment
            )
    return redirect('chat_room', user_id=user_id)


@login_required
def fetch_messages(request, user_id):
    """AJAX endpoint — returns new messages as JSON for auto-refresh."""
    other_user = get_object_or_404(CustomUser, id=user_id)
    after_id   = request.GET.get('after', 0)

    msgs = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user,   receiver=request.user),
        id__gt=after_id
    ).order_by('timestamp')

    # Mark fetched messages as read
    msgs.filter(receiver=request.user, is_read=False).update(is_read=True)

    from django.utils.html import escape
    data = [{
        'id':        m.id,
        'sender':    m.sender.get_full_name() or m.sender.username,
        'sender_id': m.sender.id,
        'message':   escape(m.message),
        'timestamp': m.timestamp.strftime('%b %d, %Y %H:%M'),
        'is_me':     m.sender == request.user,
        'attachment_url': m.attachment.url if m.attachment else None,
        'attachment_name': m.attachment.name.split('/')[-1] if m.attachment else None
    } for m in msgs]

    return JsonResponse({'messages': data})


@login_required
def group_chat(request, course_id):
    """Group chat for all members of a course."""
    course = get_object_or_404(Course, id=course_id)

    # Check access — must be teacher or enrolled student
    is_teacher  = course.teacher == request.user
    is_enrolled = Enrollment.objects.filter(
        student=request.user, course=course
    ).exists()

    if not is_teacher and not is_enrolled:
        from django.contrib import messages as django_messages
        django_messages.error(request, 'You do not have access to this group chat.')
        return redirect('course_list')

    if request.method == 'POST':
        text = request.POST.get('message', '').strip()
        attachment = request.FILES.get('attachment')
        if text or attachment:
            GroupMessage.objects.create(
                course=course,
                sender=request.user,
                message=text,
                attachment=attachment
            )
        return redirect('group_chat', course_id=course_id)

    group_messages = GroupMessage.objects.filter(course=course).order_by('timestamp')
    members        = Enrollment.objects.filter(course=course).select_related('student')

    return render(request, 'chat/group_chat.html', {
        'course':         course,
        'group_messages': group_messages,
        'members':        members,
        'is_teacher':     is_teacher,
    })


@login_required
def fetch_group_messages(request, course_id):
    """AJAX endpoint for group chat auto-refresh."""
    course   = get_object_or_404(Course, id=course_id)
    
    # Check access — must be teacher or enrolled student
    is_teacher  = course.teacher == request.user
    is_enrolled = Enrollment.objects.filter(
        student=request.user, course=course
    ).exists()

    if not is_teacher and not is_enrolled:
        return JsonResponse({'error': 'Access Denied'}, status=403)

    after_id = request.GET.get('after', 0)

    msgs = GroupMessage.objects.filter(
        course=course, id__gt=after_id
    ).order_by('timestamp')
    from django.utils.html import escape
    data = [{
        'id':        m.id,
        'sender':    m.sender.get_full_name() or m.sender.username,
        'sender_id': m.sender.id,
        'message':   escape(m.message),
        'timestamp': m.timestamp.strftime('%b %d, %Y %H:%M'),
        'is_me':     m.sender == request.user,
        'attachment_url': m.attachment.url if m.attachment else None,
        'attachment_name': m.attachment.name.split('/')[-1] if m.attachment else None
    } for m in msgs]

    return JsonResponse({'messages': data})
