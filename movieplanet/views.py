from django.shortcuts import render,redirect
from django.contrib.auth import authenticate, login,logout
from django.urls import reverse
from django.http import JsonResponse
from django.http import HttpResponse, HttpResponseRedirect
from movieplanet.models import *
from django.db.models import Q
from django.contrib import messages 
from django.conf import settings
from django.db.models import Prefetch
# from decimal import Decimal
import json
from django.http import JsonResponse
from django.core.serializers.json import DjangoJSONEncoder
# import os
# import openpyxl
import random
from django.core.mail import send_mail
from datetime import datetime
from datetime import time
from movieplanet.tasks import send_welcome_email
from movieplanet.decorators import (
   permission_required,xhr_request_only
)
######### Admin ##########


def dashboard(request):
    return render(request,"movieplanet/admin/dashboard.html")

@permission_required('Permission')
def permission(request,*args,**kwargs):
   if 'Permission' in kwargs.get('module') and kwargs.get('access'):
      roleId = kwargs.get('role', '')
      module = Module.objects.using('movieplanet').all()
      if request.method == 'POST' and 'View' in kwargs.get('permission'):
            if roleId and 'Edit' in kwargs.get('permission'):
                for m in module:
                    perm = Permission.objects.using('movieplanet').filter(modules_id=m.id,role_id=roleId).first()
                    if m.parent_id=='':
                        if perm:
                              if m.module in request.POST:
                                perm.permission =  request.POST[m.module]
                                perm.save()
                              else:
                                perm.delete()
                        else:
                              if m.module in request.POST:
                                 Permission.objects.using('movieplanet').create(
                                    permission=request.POST[m.module],
                                    role_id = roleId,
                                    modules_id = m.id
                                 )
                    else:
                        if m.parent_id:
                              permission = ''
                              if m.module+'[view]' in request.POST:
                                    permission += request.POST[m.module+'[view]']
                              if m.module+'[add]' in request.POST:
                                    permission +=','+request.POST[m.module+'[add]']
                              if m.module+'[edit]' in request.POST:
                                    permission +=','+request.POST[m.module+'[edit]']
                              if m.module+'[delete]' in request.POST:
                                    permission +=','+request.POST[m.module+'[delete]']
                                       
                              if perm:
                                    if permission:
                                       perm.permission =  permission
                                       perm.save()
                                    else:
                                       perm.delete()  
                              else:
                                  if permission:
                                     Permission.objects.using('movieplanet').create(
                                          permission=permission,
                                          role_id = roleId,
                                          modules_id = m.id,
                                          module_parent_id=m.parent_id
                                     )
                                   
                return HttpResponseRedirect(reverse('movieplanet:permission', args=[roleId]))       
            return redirect(reverse('movieplanet:permissions'))
      
      elif request.method == 'PUT' and request.headers.get('x-requested-with') == 'XMLHttpRequest' and 'View' in kwargs.get('permission'):
            data = json.loads(request.body)
            # start = request.POST['start']
            # length = request.POST['length']
            # search = request.POST['search']
            start = int(data.get('start', 1))
            length = int(data.get('length', 10))
            search = data.get('search', '')
            startIndex = (int(start)-1) * int(length)
            endIndex = startIndex + int(length)
            listData = []
            roles = kwargs.get('roleIds')
            if search :
                  data = Role.objects.using('movieplanet').filter(name__icontains=search,id__in=roles)[startIndex:endIndex].all()
                  totalLen = list(Role.objects.using('movieplanet').filter(name__icontains=search,id__in=roles).all())
            else:
                  data = Role.objects.using('movieplanet').filter(id__in=roles)[startIndex:endIndex].all()
                  totalLen = list(Role.objects.using('movieplanet').filter(id__in=roles).all())

            for i in data:
                  permission = {
                  "id":i.id,
                  "roleName":i.name,
                  "action":(f'<a class="btn btn-primary" href="{settings.BASE_URL}movieplanet/admin/administration/permission/{i.id}" >Permission</a>')
                  }
                  listData.append(permission)

            return JsonResponse({
                  "success": True,
                  "iTotalRecords":len(totalLen),
                  "iTotalDisplayRecords":len(totalLen),
                  "aaData":listData
            }, status=200)   
      else:
            if roleId and 'Edit' in kwargs.get('permission'):
                  allow = '<ul class="list-group">'
                  for m in module:
                        perm = Permission.objects.using('movieplanet').filter(modules_id=m.id,role_id=roleId).first()
                        if m.parent_id=='':
                              allow +=(f'<li class="list-group-item ">'
                                          f'<div class="w-100 d-flex justify-content-between">'
                                          f'<div>{m.module}</div>'
                                          f'<div>View <input type="checkbox" name="{m.module}" value="View" {"checked" if perm else None} class="form-check-input" /> </div>'
                                          f'</div>'
                                          f'{checkParent(roleId,module,m.id)}'
                                          f'</li>')   
                  
                  allow +='</ul>'
                  return render(request,"movieplanet/admin/allowpermission.html",{'permissions':allow})
            
            return render(request,"movieplanet/admin/permission.html")
   else:
      return render(request,"movieplanet/404.html")  
   
def checkParent(role,module,mid):
      allow = '<ul class="list-group">'
      for m in module:
            perm = Permission.objects.using('movieplanet').filter(modules_id=m.id,role_id=role).first()
            if m.parent_id == str(mid):
                        checked = []
                        if perm:
                           checked = perm.permission.split(',')
                       
                        allow +=(f'<li class="list-group-item">'
                                    f'<div class="w-100 d-flex justify-content-between">'
                                    f'<div>{m.module}</div>'
                                    f'<div>View <input name="{m.module}[view]" type="checkbox" value="View" {"checked" if "View" in checked else None } class="form-check-input" />'
                                    f'Add <input name="{m.module}[add]" type="checkbox" value="Add" {"checked" if "Add" in checked else None }  class="form-check-input" />' 
                                    f'Edit <input name="{m.module}[edit]" type="checkbox" value="Edit" {"checked" if "Edit" in checked else None } class="form-check-input" />'
                                    f'Delete <input name="{m.module}[delete]" type="checkbox" value="Delete" {"checked" if "Delete" in checked else None } class="form-check-input" /></div>'
                                    f'</div>'
                                    f'{checkParent(role,module,m.id)}'
                                 f'</li>')   
                 
      allow +='</ul>'
      
      return allow

@permission_required('Menu') 
def menu(request,*args,**kwargs):
    if 'Menu' in kwargs.get('module') and kwargs.get('access'):
      parentId = kwargs.get('parentId', None)
      menuId = kwargs.get('menuId', None)
      action = {}
      if request.method == 'POST' and 'View' in kwargs.get('permission'):
            if menuId =='create' and 'Add' in kwargs.get('permission'):
                  Menu.objects.using('movieplanet').create(
                   name=request.POST['menu'], 
                   link=request.POST['link'],
                   type=request.POST['type'],
                   menuId=parentId,
                   status=1
                  )
                  return HttpResponseRedirect(reverse('movieplanet:menus')) 
            elif int(menuId) and 'Edit' in kwargs.get('permission'):
                  if parentId:
                     update = Menu.objects.using('movieplanet').filter(menuId=parentId,id=menuId).first()
                  else:
                     update = Menu.objects.using('movieplanet').filter(id=menuId).first()
                  if update:
                        update.name = request.POST['menu']
                        update.link = request.POST['link']
                        update.save()
                        if parentId:
                           return HttpResponseRedirect(reverse('movieplanet:menu', args=[menuId, parentId]))
                        return HttpResponseRedirect(reverse('movieplanet:menu', args=[menuId]))
            return HttpResponseRedirect(reverse('movieplanet:menus'))  
            # previous_url = request.META.get('HTTP_REFERER', '/')
            # return redirect(previous_url)
      elif request.method == 'PUT' and 'View' in kwargs.get('permission'):
            data = json.loads(request.body)
            parentId = kwargs.get('parentId', None)
            start = int(data.get('start', 1))
            length = int(data.get('length', 10))
            search = data.get('search', '')
            startIndex = (int(start)-1) * int(length)
            endIndex = startIndex + int(length)
            listData = []
            if search :
                  data = Menu.objects.using('movieplanet').filter(Q(menuId=parentId),name__icontains=search)[startIndex:endIndex]
                  totalLen = Menu.objects.using('movieplanet').filter(Q(menuId=parentId),name__icontains=search).count()
            else:
                  data = Menu.objects.using('movieplanet').filter(Q(menuId=parentId))[startIndex:endIndex]
                  totalLen = Menu.objects.using('movieplanet').filter(Q(menuId=parentId)).count()


            for i in data:
                  action_btn = ''
                  if 'Edit' in kwargs.get('permission'):
                      if parentId:
                        action_btn += f'<a class="btn btn-primary" href="{settings.BASE_URL}movieplanet/admin/website/menu/{i.id}/{parentId}">Edit</a>' 
                      else:
                        action_btn += f'<a class="btn btn-primary" href="{settings.BASE_URL}movieplanet/admin/website/menu/{i.id}">Edit</a>'   
                  if 'Delete' in kwargs.get('permission'):
                      # action_btn += f'<a class="btn btn-danger" href="{settings.BASE_URL}movieplanet/admin/website/menu/{i.id}">Delete</a>' 
                      action_btn += f'<button class="btn btn-danger" onclick="deleteModal({i.id})">Delete</button>' 
                  if i.type==2:
                     link = (f'<a href="{settings.BASE_URL}movieplanet/admin/website/menus/{i.id}">{i.name}</a>')
                  else:
                      link = i.name
                  permission = {
                  "id":i.id,
                  "name":link,
                  "action":action_btn
                  }
                  listData.append(permission)
 
            return JsonResponse({
            "success": True,
            "iTotalRecords":totalLen,
            "iTotalDisplayRecords":totalLen,
            "aaData":listData,
            "action":action
            }, status=200)
      elif request.method == 'PATCH' and 'Edit' in kwargs.get('permission'):
            data = json.loads(request.body)
            Menu.objects.using('movieplanet').filter(id=data.get('id')).delete()
            Menu.objects.using('movieplanet').filter(menuId=data.get('id')).delete()
           
            return JsonResponse({
                  "status": True,
                  "msg":"Item delete successfully!"
            }, status=200)
           
      else:

            if 'Add' in kwargs.get('permission'):
               action['add'] = f'<a class="btn btn-primary"  href="{settings.BASE_URL}movieplanet/admin/website/menu/create">Add</a>'

            if 'Add' in kwargs.get('permission'):
               if parentId:
                  action['add'] = f'<a class="btn btn-primary" href="{settings.BASE_URL}movieplanet/admin/website/menu/create/{parentId}">Add</a>'
               else:
                  action['add'] = f'<a class="btn btn-primary" href="{settings.BASE_URL}movieplanet/admin/website/menu/create">Add</a>'
           
            if menuId=='create' and 'Add' in kwargs.get('permission'):
               if parentId and Menu.objects.using('movieplanet').filter(id=parentId,type=2).exists():
                  return render(request,"movieplanet/admin/menuedit.html") 
               elif parentId is None:
                  return render(request,"movieplanet/admin/menuedit.html")  
               else:
                  return HttpResponseRedirect(reverse('movieplanet:menus')) 
            elif menuId and 'Edit' in kwargs.get('permission'):
               if parentId:
                  menu = Menu.objects.using('movieplanet').filter(id=menuId,menuId=parentId).values().first()
               else:
                  menu = Menu.objects.using('movieplanet').filter(id=menuId).values().first()
               if menu:
                  return render(request,"movieplanet/admin/menuedit.html",{"menu":menu})
               return HttpResponseRedirect(reverse('movieplanet:menus')) 

            return render(request,"movieplanet/admin/menu.html",{"action":action})


    else:
      return render(request,"movieplanet/404.html")   

def menuFind(menus, pid):
    result = []
    for m in menus:
        if 'parentId' in m and m['parentId'] == pid:
            result.append(m) 
    return result

@permission_required('Posts') 
def posts(request,*args,**kwargs):
    
    if 'Posts' in kwargs.get('module') and kwargs.get('access'):
      parentId = kwargs.get('parentId', None)
      postId = kwargs.get('postId', None)
      action = {}
      if request.method == 'POST' and 'View' in kwargs.get('permission'):
            if postId=='create' and 'Add' in kwargs.get('permission'):
                  post = request.POST
                  Posts.objects.using('movieplanet').create(
                        name=post.get('name', ''),
                        image=post.get('image', ''),
                        rate=post.get('rate', ''),
                        size=post.get('size', ''),
                        type=post.get('type', ''),
                        genre=post.get('genre', ''),
                        lang=post.get('lang', ''),
                        status=post.get('status', ''),
                        starcast=post.get('starcast', ''),
                        story=post.get('story', ''),
                        link=post.get('link', ''),
                        menu=post.get('menu', ''),
                        parent=parentId,
                        duration=post.get('duration', ''),
                        release_date=post.get('release_date', '')
                  )
                  return HttpResponseRedirect(reverse('movieplanet:posts')) 
            elif int(postId) and 'Edit' in kwargs.get('permission'):
                  post = request.POST
                  if parentId:
                     update = Posts.objects.using('movieplanet').filter(parent=parentId,id=postId).first()
                  else:
                     update = Posts.objects.using('movieplanet').filter(id=postId).first()
                  if update:
                        update.image = post.get('image', '')
                        update.rate = post.get('rate', '')
                        update.size = post.get('size', '')
                        update.genre = post.get('genre', '')
                        update.lang = post.get('lang', '')
                        update.status = post.get('status', '')
                        update.starcast = post.get('starcast', '')
                        update.story = post.get('story', '')
                        update.link = post.get('link', '')
                        update.menu = post.get('menu', '')
                        update.duration=post.get('duration', '')
                        update.release_date = post.get('release_date', '')
                        update.save()
                        if parentId:
                           return HttpResponseRedirect(reverse('movieplanet:post', args=[postId, parentId]))
                        return HttpResponseRedirect(reverse('movieplanet:post', args=[postId]))
            return HttpResponseRedirect(reverse('movieplanet:posts'))             
            # previous_url = request.META.get('HTTP_REFERER', '/')
            # return redirect(previous_url)
      elif request.method == 'PUT' and 'View' in kwargs.get('permission'):
            data = json.loads(request.body)
            # start = request.POST['start']
            # length = request.POST['length']
            # search = request.POST['search']
            start = int(data.get('start', 1))
            tickall = int(data.get('tickall', False))
            length = int(data.get('length', 10))
            search = data.get('search', '')
            startIndex = (int(start)-1) * int(length)
            endIndex = startIndex + int(length)
            item = data.get('item', [])
            status = data.get('status', '')
            trand = data.get('trand', '')
            if status=="1" or status=="0":
               for i in item:
                   if i['check']:
                      Posts.objects.using('movieplanet').filter(id=i['id']).update(status=status)

            if trand=="1" or trand=="0":
               for i in item:
                   if i['check']:
                      if trand == "1":
                         if not Trand.objects.using('movieplanet').filter(post_id=i['id']).exists():
                              Trand.objects.using('movieplanet').create(
                              post_id=i['id'],
                              status=1
                              )
                      elif trand == "0":
                         Trand.objects.using('movieplanet').filter(post_id=i['id']).delete()
            
            if search :
                  data = Posts.objects.using('movieplanet').filter(Q(parent=parentId),name__icontains=search)[startIndex:endIndex].all()
                  totalLen = Posts.objects.using('movieplanet').filter(Q(parent=parentId),name__icontains=search).count()
            
            else:
                  data = Posts.objects.using('movieplanet').filter(Q(parent=parentId)).all()[startIndex:endIndex]
                  totalLen = Posts.objects.using('movieplanet').filter(Q(parent=parentId)).count()
            
            listData = []
            for i in data:
                  
                  btn =''
                  if 'Edit' in kwargs.get('permission'):
                     if parentId:
                        btn += f'<a class="btn btn-primary" href="{settings.BASE_URL}movieplanet/admin/website/post/{i.id}/{parentId}" >Edit</a>'
                     else:
                        btn += f'<a class="btn btn-primary" href="{settings.BASE_URL}movieplanet/admin/website/post/{i.id}" >Edit</a>'  
                  if 'Delete' in kwargs.get('permission'):
                     btn += f'<button class="btn btn-danger" onclick="deleteModal({i.id})">Delete</button>'
                  
                  link = i.name
                  if i.type==2:
                     link = f'<a href="{settings.BASE_URL}movieplanet/admin/website/posts/{i.id}" >{i.name}</a>'
                  
                  trand = i.trands.first()
                  if trand and trand.post_id == i.id:
                     trow = '<span class="badge bg-primary">Trand</span>'
                  else:
                      trow = ''

                  post = {
                        "id":f'<div class="d-flex justify-content-between"><span>{i.id}</span> <input type="checkbox" {"checked" if tickall else ""} name="item[{i.id}]" value="{i.id}" class="item" /></div>',
                        "name":link,
                        # "image":f'<img src={i.image}/>',
                        "trand":trow,
                        "rate":i.rate,
                        "status":(
                        '<span class="badge bg-success">Active</span>' if i.status == "1"
                        else '<span class="badge bg-danger">Deactive</span>'
                        ),
                        "action":btn
                  }
                        
                  listData.append(post)
            if 'Edit' in kwargs.get('permission'):
                action['status'] = """
                                    <div class="dropdown">
                                          <button class="btn border dropdown-toggle" type="button" id="dropdownMenu" data-bs-toggle="dropdown" aria-expanded="false">
                                            Status update
                                          </button>
                                          <ul class="dropdown-menu"  aria-labelledby="dropdownMenu">
                                                <li>
                                                      <select name="status" class="form-select me-2" id="status-update" >
                                                            <option value="">Status</option>
                                                            <option value="1">Active</option>
                                                            <option value="0">Deactive</option>
                                                      </select>    
                                                </li>
                                                <li>
                                                      <select name="trand" class="form-select me-2" id="trand-update" >
                                                            <option value="">Trand</option>
                                                            <option value="1">Active</option>
                                                            <option value="0">Deactive</option>
                                                      </select>  
                                                </li>
                                                
                                          </ul>
                                    </div>
                                                                  
                                   """


            return JsonResponse({
                  "success": True,
                  "iTotalRecords":totalLen,
                  "iTotalDisplayRecords":totalLen,
                  "aaData":listData,
                  "action":action
            }, status=200)
      elif request.method == 'PATCH' and 'Delete' in kwargs.get('permission'):
            data = json.loads(request.body)
            Posts.objects.using('movieplanet').filter(id=data.get('id')).delete()
            Posts.objects.using('movieplanet').filter(parent=data.get('id')).delete()
            return JsonResponse({
                  "status": True,
                  "msg":"Item delete successfully!"
            }, status=200)
      else:
            if 'Add' in kwargs.get('permission'):
               if parentId:
                  action['add'] = f'<a class="btn btn-primary" href="{settings.BASE_URL}movieplanet/admin/website/post/create/{parentId}">Add</a>'
               else:
                  action['add'] = f'<a class="btn btn-primary" href="{settings.BASE_URL}movieplanet/admin/website/post/create">Add</a>'
                  action['excel'] = f'<a class="btn btn-info" href="{settings.BASE_URL}movieplanet/admin/website/post/excel">Excel</a>'
            if postId=='create' and 'Add' in kwargs.get('permission'):
               if parentId: 
                  if Posts.objects.using('movieplanet').filter(id=parentId,type=2).exists():
                     return render(request,"movieplanet/admin/postedit.html") 
                  return HttpResponseRedirect(reverse('movieplanet:posts', args=[parentId]))
               return render(request,"movieplanet/admin/postedit.html")  
               
            elif postId and 'Edit' in kwargs.get('permission'):
               post = Posts.objects.using('movieplanet').filter(Q(parent=parentId),id=postId).values().first()
               if post:
                  return render(request,"movieplanet/admin/postedit.html",{"post":post})
               return HttpResponseRedirect(reverse('movieplanet:posts')) 
            return render(request,"movieplanet/admin/post.html",{"action":action})
    else:
      return render(request,"movieplanet/404.html")  


@permission_required('Users')    
def customers(request,*args,**kwargs):
   if 'Users' in kwargs.get('module') and kwargs.get('access'):
      userId = kwargs.get('userId', None)

      if request.method == 'POST' and 'Edit' in kwargs.get('permission'):
            uids = checkRoles(kwargs.get('authId'),kwargs.get('roleIds'),[])
            if userId not in uids and Roles.objects.using('movieplanet').filter(user_id=userId, role_id__in=kwargs.get('roleIds')).exclude(user_id=kwargs.get('authId')).exists(): 
                  post = request.POST
                  roles = Roles.objects.using('movieplanet').filter(user_id=kwargs.get('authId')).exclude(role__name='User').all()
                  for r in roles:
                      if r.role.name in request.POST:
                              if Roles.objects.using('movieplanet').filter(user_id=userId, role_id = r.role_id).exists():
                                    if kwargs.get('authId') in uids:
                                       uids.remove(kwargs.get('authId'))
                                    urole = Roles.objects.using('movieplanet').filter(user_id=userId, role_id = r.role_id).exclude(given_id__in=uids).first()
                                    if urole:
                                       urole.given_id = kwargs.get('authId')
                                       urole.save()
                              else:
                                    Roles.objects.using('movieplanet').create(
                                    user_id = userId,
                                    role_id = r.role_id,
                                    given_id = kwargs.get('authId')
                                    )
                      elif Roles.objects.using('movieplanet').filter(user_id=userId, role_id = r.role_id).exists():
                              urole = Roles.objects.using('movieplanet').filter(user_id=userId, role_id = r.role_id).exclude(given_id__in=uids).first()
                              if urole:
                                 urole.delete()
                  return HttpResponseRedirect(reverse('movieplanet:user', args=[userId]))
            return HttpResponseRedirect(reverse('movieplanet:users')) 
      elif  request.method == 'PUT' and 'View' in kwargs.get('permission'):
            data = json.loads(request.body)
            start = int(data.get('start', 1))
            length = int(data.get('length', 10))
            search = data.get('search', '')
            startIndex = (int(start)-1) * int(length)
            endIndex = startIndex + int(length)
            listData = []
            totalLen=0
            if len(kwargs.get('roleIds')) > 1:
                  cids = checkRoles(kwargs.get('authId'),kwargs.get('roleIds'),[kwargs.get('authId')])
                  
                  if search:
                        data = Customer.objects.using('movieplanet').filter(is_admin="0",name__icontains=search).exclude(id__in=cids).filter(roles__role_id__in=kwargs.get('roleIds')).distinct()[startIndex:endIndex]
                        totalLen = Customer.objects.using('movieplanet').filter(is_admin="0",name__icontains=search).exclude(id__in=cids).filter(roles__role_id__in=kwargs.get('roleIds')).distinct().count()
                  else:
                        data = Customer.objects.using('movieplanet').filter(is_admin="0").exclude(id__in=cids).filter(roles__role_id__in=kwargs.get('roleIds')).distinct()[startIndex:endIndex]
                        totalLen = Customer.objects.using('movieplanet').filter(is_admin="0",name__icontains=search).exclude(id__in=cids).filter(roles__role_id__in=kwargs.get('roleIds')).distinct().count()

                  for i in data:
                        # assignId = list(i.roles.values_list('given_id', flat=True).distinct())
                        # roleIds = list(i.roles.values_list('role_id', flat=True))
                        # if any(role in roleIds for role in kwargs.get('roleIds')):
                        btn =''
                        if 'Edit' in kwargs.get('permission'):
                              btn += f'<a class="btn btn-primary" href="{settings.BASE_URL}movieplanet/admin/administration/user/{i.id}" >Edit</a>'
                        post = {
                              "id":i.id,
                              "name":i.name,
                              "email":i.email,
                              "action":btn
                        }
                        listData.append(post)
            
            return JsonResponse({
                        "success": True,
                        "iTotalRecords":totalLen,
                        "iTotalDisplayRecords":totalLen,
                        "aaData":listData
                  }, status=200)
      
      else:
            if userId and 'Edit' in kwargs.get('permission'):
               uids = checkRoles(kwargs.get('authId'),kwargs.get('roleIds'),[])
               if userId not in uids and Roles.objects.using('movieplanet').filter(user_id=userId, role_id__in=kwargs.get('roleIds')).exclude(user_id=kwargs.get('authId')).exists():
                  # uids.remove(kwargs.get('authId'))
                  # merged = list(dict.fromkeys(uroles + kwargs.get('roleIds')))

                  roles = Roles.objects.using('movieplanet').filter(user_id=kwargs.get('authId')).exclude(role__name='User').all()
                  allowRoles = []
                  for r in roles:                     
                      if Roles.objects.using('movieplanet').filter(user_id=userId, role_id = r.role_id).exists():
                         if kwargs.get('authId') in uids:
                            uids.remove(kwargs.get('authId'))
                         urole = Roles.objects.using('movieplanet').filter(user_id=userId, role_id = r.role_id).exclude(given_id__in=uids).first()
                         if urole:
                              r.assign = 1
                              allowRoles.append(r) 
                      else:
                         allowRoles.append(r) 

                  return render(request,"movieplanet/admin/useredit.html",{"roles":allowRoles})
               return HttpResponseRedirect(reverse('movieplanet:users')) 
            return render(request,"movieplanet/admin/user.html")
      # return HttpResponseRedirect(request.META['HTTP_REFERER']) 
   else:
      return render(request,"movieplanet/404.html")  

def checkRoles(aid, rids, collected=None):
    if collected is None:
       collected = []
    if Customer.objects.using('movieplanet').filter(id=aid,is_admin=1).exists():
       return collected
    data = Customer.objects.using('movieplanet').exclude(id=aid).all()
    gids = list(Roles.objects.using('movieplanet').filter(user_id=aid).filter(
           ~Q(given_id=None)
           ).values('given_id', 'role_id').distinct())
    ids = list(set(map(lambda x: x['given_id'], gids)))


    for i in data:
      cgids = list(i.roles.filter(
      ~Q(given_id=None)
      ).values('given_id', 'role_id').distinct())
     
      if i.is_admin == 1:
         collected.append(i.id) 
      elif all(item in cgids for item in gids):  
           collected.append(i.id) 
      elif i.id in ids and i.id not in collected:
           collected.append(i.id)
           checkRoles(i.id, rids, collected)
    return collected   

@permission_required('Chat')   
def chat(request,*args,**kwargs):
    if 'Chat' in kwargs.get('module') and kwargs.get('access'):
      return render(request,"movieplanet/admin/chat.html")
    else:
      return render(request,"movieplanet/404.html")  

@permission_required('Module') 
def modules(request,*args,**kwargs):
    if 'Module' in kwargs.get('module') and kwargs.get('access'):
      parentId = kwargs.get('parentId', '')
      moduleId = kwargs.get('moduleId', '')
      action = {}
      if request.method == 'POST' and 'View' in kwargs.get('permission'):
            if moduleId =='create' and 'Add' in kwargs.get('permission'):
               Module.objects.using('movieplanet').create(
                  module=request.POST['module'], 
                  url=request.POST['url'],
                  moduleType=request.POST['type'],
                  parent_id=parentId
               )
            elif int(moduleId) and 'Edit' in kwargs.get('permission'):
                  if parentId:
                     update = Module.objects.using('movieplanet').filter(parent_id=parentId,id=moduleId).first()
                  else:
                     update = Module.objects.using('movieplanet').filter(id=moduleId).first()
                  if update:
                        update.module = request.POST['module']
                        update.url = request.POST['url']
                        update.save()
                        if parentId:
                           return HttpResponseRedirect(reverse('movieplanet:module', args=[moduleId, parentId]))
                        return HttpResponseRedirect(reverse('movieplanet:module', args=[moduleId]))
            return HttpResponseRedirect(reverse('movieplanet:modules'))      


      elif request.method == 'PUT' and 'View' in kwargs.get('permission'):
            data = json.loads(request.body)
            parentId = kwargs.get('parentId', '')
            start = int(data.get('start', 1))
            length = int(data.get('length', 10))
            search = data.get('search', '')
            startIndex = (int(start)-1) * int(length)
            endIndex = startIndex + int(length)
            listData = []
            if search :
                  data = Module.objects.using('movieplanet').filter(Q(parent_id=parentId),name__icontains=search)[startIndex:endIndex]
                  totalLen = Module.objects.using('movieplanet').filter(Q(parent_id=parentId),name__icontains=search).count()
            else:
                  data = Module.objects.using('movieplanet').filter(Q(parent_id=parentId))[startIndex:endIndex]
                  totalLen = Module.objects.using('movieplanet').filter(Q(parent_id=parentId)).count()

            for i in data:
                  action_btn = ''
                  if 'Edit' in kwargs.get('permission'):
                      if parentId:
                        action_btn += f'<a class="btn btn-primary" href="{settings.BASE_URL}movieplanet/admin/setting/module/{i.id}/{parentId}">Edit</a>' 
                      else:
                        action_btn += f'<a class="btn btn-primary" href="{settings.BASE_URL}movieplanet/admin/setting/module/{i.id}">Edit</a>'   
                  if 'Delete' in kwargs.get('permission'):
                      action_btn += f'<button class="btn btn-danger" onclick="deleteModal({i.id})">Delete</button>' 
                  if i.moduleType=="2":
                     link = (f'<a href="{settings.BASE_URL}movieplanet/admin/setting/modules/{i.id}">{i.module}</a>')
                  else:
                      link = i.module
                  permission = {
                  "id":i.id,
                  "module":link,
                  "action":action_btn
                  }
                  listData.append(permission)
 
            return JsonResponse({
            "success": True,
            "iTotalRecords":totalLen,
            "iTotalDisplayRecords":totalLen,
            "aaData":listData,
            "action":action
            }, status=200)
      elif request.method == 'PATCH' and 'Edit' in kwargs.get('permission'):
            data = json.loads(request.body)
            Module.objects.using('movieplanet').filter(id=data.get('id')).delete()
            Module.objects.using('movieplanet').filter(parent_id=data.get('id')).delete()
           
            return JsonResponse({
                  "status": True,
                  "msg":"Item delete successfully!"
            }, status=200)
           
      else:

            if 'Add' in kwargs.get('permission'):
               if parentId:
                  action['add'] = f'<a class="btn btn-primary" href="{settings.BASE_URL}movieplanet/admin/setting/module/create/{parentId}">Add</a>'
               else:
                  action['add'] = f'<a class="btn btn-primary" href="{settings.BASE_URL}movieplanet/admin/setting/module/create">Add</a>'
           
            if moduleId=='create' and 'Add' in kwargs.get('permission'):
               if parentId:
                  if Module.objects.using('movieplanet').filter(id=parentId,moduleType="2").exists():
                     return render(request,"movieplanet/admin/moduleedit.html") 
                  return HttpResponseRedirect(reverse('movieplanet:modules', args=[parentId]))
               return render(request,"movieplanet/admin/moduleedit.html")  
               
            
            elif moduleId and 'Edit' in kwargs.get('permission'):
               module = Module.objects.using('movieplanet').filter(Q(parent_id=parentId),id=moduleId).values().first()

               if module:
                  return render(request,"movieplanet/admin/moduleedit.html",{"module":module})
               return HttpResponseRedirect(reverse('movieplanet:modules')) 

            return render(request,"movieplanet/admin/module.html",{"action":action})


    else:
      return render(request,"movieplanet/404.html")   


@xhr_request_only()
def sidebarList(request,*args,**kwargs):
   modules = kwargs.get('module')
   sidebarList =  list(Module.objects.using('movieplanet').filter(module__in=modules,status=1).values())
   return JsonResponse({
      "success": True,
      "data":sidebarList
   }, status=200)   


@permission_required('Profile')
def profile(request,*args,**kwargs):
    if 'Profile' in kwargs.get('module') and kwargs.get('access'):
      if request.method == 'POST' and 'View' in kwargs.get('permission'):
         pass 
      elif request.method == 'PUT' and 'View' in kwargs.get('permission'):
           pass
      elif request.method == 'PATCH' and 'Edit' in kwargs.get('permission'):
           pass
      else:
            profile = Customer.objects.using('movieplanet').filter(id=kwargs.get('authId')).first()
          
            return render(request,"movieplanet/admin/profile.html",{"profile":profile})
    else:
      return render(request,"movieplanet/404.html")   

@permission_required('Comments')
def comments(request,*args,**kwargs):
    if 'Comments' in kwargs.get('module') and kwargs.get('access'):
      action = {}
      if request.method == 'POST' and 'View' in kwargs.get('permission'):
         pass 
      elif request.method == 'PUT' and 'View' in kwargs.get('permission'):
            data = json.loads(request.body)
            tickall = int(data.get('tickall', False))
            start = int(data.get('start', 1))
            length = int(data.get('length', 10))
            search = data.get('search', '')
            startIndex = (int(start)-1) * int(length)
            endIndex = startIndex + int(length)
            listData = []
            item = data.get('item', [])
            status = data.get('status', '')
            if status=="1" or status=="0":
               for i in item:
                   if i['check']:
                      Comments.objects.using('movieplanet').filter(id=i['id']).update(status=status)

            if search :
                  data = Comments.objects.using('movieplanet').filter(post__name__icontains=search)[startIndex:endIndex]
                  totalLen = Comments.objects.using('movieplanet').filter(post__name__icontains=search).count()
            else:
                  data = Comments.objects.using('movieplanet')[startIndex:endIndex]
                  totalLen = Comments.objects.using('movieplanet').count()

            for i in data:
                  action_btn = ''
                  if 'Delete' in kwargs.get('permission'):
                      action_btn += f'<button class="btn btn-danger" onclick="deleteModal({i.id})">Delete</button>' 
                  
                  status = '<span class="badge bg-danger">Pending</span>'
                  if i.status == "1":
                     status = '<span class="badge bg-success">Approved</span>'
                  
                  permission = {
                  "id":f'<div class="d-flex justify-content-between"><span>{i.id}</span> <input type="checkbox" {"checked" if tickall else ""} name="item[{i.id}]" value="{i.id}" class="item" /></div>',
                  "post":i.post.name,
                  "comment":i.msg,
                  "status":status,
                  "action":action_btn
                  }
                  listData.append(permission)
            if 'Edit' in kwargs.get('permission'):
                action['status'] = """
                                    <select name="status" class="me-2 px-2" id="status-update" >
                                          <option value="">Status</option>
                                          <option value="1">Active</option>
                                          <option value="0">Deactive</option>
                                    </select>  
                                                                  
                                   """
 
            return JsonResponse({
            "success": True,
            "iTotalRecords":totalLen,
            "iTotalDisplayRecords":totalLen,
            "aaData":listData,
            "action":action
            }, status=200)
      elif request.method == 'PATCH' and 'Edit' in kwargs.get('permission'):
            data = json.loads(request.body)
            Comments.objects.using('movieplanet').filter(id=data.get('id')).delete()
            return JsonResponse({
                  "status": True,
                  "msg":"Item delete successfully!"
            }, status=200)
      else:

            return render(request,"movieplanet/admin/comment.html")
    else:
      return render(request,"movieplanet/404.html")   

############# Auth ############
def login(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        customer = Customer.authenticate(email=email, password=password)
        if customer:
            request.session['customer'] = json.loads(
                  json.dumps({
                        'id': customer.id,
                        'name': customer.name,
                        'email': customer.email,
                        'is_admin':customer.is_admin
                  }, cls=DjangoJSONEncoder)
            )
            return redirect('admin/dashboard')
            # return HttpResponse(f"Welcome {customer.name}!")
        else:
            return HttpResponseRedirect(reverse('movieplanet:movieplanet-login'))
    else:
      return render(request,"movieplanet/login.html")
 
def signup(request):
    if request.method == 'POST':
        email = request.POST['email']
        name = request.POST['name']
        password = request.POST['password']
        if Customer.objects.using('movieplanet').filter(email=email).exists():
            messages.error(request, "Email already exists. Please log in or use another email.")
            return HttpResponseRedirect(reverse('movieplanet-signup'))
        random_number = random.randint(10000, 99999)
        try:
            role = Role.objects.using('movieplanet').filter(name='User').first()
            customer = Customer(email=email, name=name, is_admin=False)
            customer.set_password(password)
            customer.email_verify = random_number
            customer.save()
            Roles.objects.create(
                  role_id=role['id'],
                  user_id=customer.id
            )
        except Exception as e:
            messages.error(request, e)
            return HttpResponseRedirect(reverse('movieplanet-signup'))

      #   send_welcome_email.delay(
      #   subject="Verify Email",
      #   message=f"Your verify code is {random_number}",
      #   recipient_email=email)
        return redirect('admin/dashboard')
        # return HttpResponseRedirect(reverse('admin/dashboard')) 
    else:
      return render(request,"movieplanet/signup.html")

def logout(request):
    request.session.flush()
    return HttpResponseRedirect(reverse('movieplanet:movieplanet-login'))
    # return HttpResponse("Logged out successfully!")

########## Frontend ################

def home(request,*args,**kwargs):
    if request.method == 'POST':
      start = request.POST['start']
      length = request.POST['length']
      search = request.POST['search']
      startIndex = (int(start)-1) * int(length)
      endIndex = startIndex + int(length)
      Link = kwargs.get('Link', None)

      rates = request.GET.get('rates', '')
      min_rate, max_rate = rates.split(',') if rates else (0, 10)

      years = request.GET.get('years', '')
      start_year, end_year = years.split(',') if years else (1900, datetime.now().year)
      
      genre = request.GET.get('genres', '')
      genres = genre.split(',') if genre else []
      # rates = request.POST.getlist('rates[]', [])
      # if len(rates) == 2:
      #    min_rate, max_rate = rates
      # else:
      #    min_rate, max_rate = 0, 10
      # print(request.GET)
      query = Q()
      for word in genres:
          query |= Q(genre__icontains=word)
      
      if Link:
            linkList = Link.split("+")
            Link = " ".join(linkList)
            parent = Posts.objects.filter(name=Link,status=1).first()
            Link = parent.id
      if search:
            data = Posts.objects.filter(query,Q(parent=Link),Q(release_date__year__gte=start_year),Q(release_date__year__lte=end_year),rate__range=(min_rate, max_rate),name__icontains=search,status=1)[startIndex:endIndex]
            totalLen = Posts.objects.filter(query,Q(parent=Link),Q(release_date__year__gte=start_year),Q(release_date__year__lte=end_year),rate__range=(min_rate, max_rate),name__icontains=search,status=1).count()
      
      else:
            data = Posts.objects.filter(query,Q(parent=Link),Q(release_date__year__gte=start_year),Q(release_date__year__lte=end_year),rate__range=(min_rate, max_rate),status=1)[startIndex:endIndex]
            totalLen = Posts.objects.filter(query,Q(parent=Link),Q(release_date__year__gte=start_year),Q(release_date__year__lte=end_year),rate__range=(min_rate, max_rate),status=1).count()

      listData = []
      for i in data:
            post = {
                  "id":i.id,
                  "name":i.name,
                  "image":i.image,
                  "rate":i.rate,
                  "type":i.type
            }     
            listData.append(post)
      
      return JsonResponse({
      "success": True,
      "iTotalRecords":totalLen,
      "iTotalDisplayRecords":totalLen,
      "aaData":listData
      }, status=200)
    else:
      baseUrl = settings.BASE_URL
      trands=Trand.objects.using('movieplanet').select_related('post').filter(status=1)[0:5]
      return render(request,"movieplanet/home.html",{"Trands":trands,"baseUrl":baseUrl})

def category(request,*args,**kwargs):
    
    if request.method == 'POST':
      start = request.POST['start']
      length = request.POST['length']
      search = request.POST['search']
      startIndex = (int(start)-1) * int(length)
      endIndex = startIndex + int(length)
      params  = kwargs.get('params')
      categories = params.replace("/", " ").split()
      query = Q()

      for word in categories:
          query &= Q(menu__icontains=word)
      if search :
            data = Posts.objects.filter(query,parent=None,name__icontains=search,status=1)[startIndex:endIndex].all()
            totalLen = Posts.objects.filter(query,parent=None,name__icontains=search,status=1).count()
      
      else:
            data = Posts.objects.filter(query,parent=None,status=1)[startIndex:endIndex].all()
            totalLen = Posts.objects.filter(query,parent=None,status=1).count()
      
      listData = []
      for i in data:
            post = {
                  "id":i.id,
                  "name":i.name,
                  "image":i.image,
                  "rate":i.rate,
                  "type":i.type
            }     
            listData.append(post)
      
      return JsonResponse({
      "success": True,
      "iTotalRecords":totalLen,
      "iTotalDisplayRecords":totalLen,
      "aaData":listData
      }, status=200)
    else:
      return render(request,"movieplanet/home.html")

def detail(request,Link=None,parentId=None):
    linkList = Link.split("+")
    MovieName = " ".join(linkList)
    
    data = Posts.objects.filter(name=MovieName,status=1).values().first()
    if request.method == 'POST':
      if request.session.get('customer'): 
            auth = request.session.get('customer')
            Comments.objects.using('movieplanet').create(
                  user_id=auth['id'],
                  msg=request.POST['msg'],
                  parentId=parentId,
                  post_id=data['id'],
                  status=0
            )
            
            return JsonResponse({
            "success": True
            }, status=200)
      else:
            return JsonResponse({
            "success": False
            }, status=404) 
    elif request.method == 'PUT':
      comments = Comments.objects.using('movieplanet').filter(Q(parentId=parentId),post=data['id']).order_by('-id').all()[0:8]
      isComment = False
      html = ''
      
      if parentId:
         html +='<ul class="list-group my-2 ml-4 comment">'  
      for c in comments:
            isComment = True
            
            if parentId:
                  html += f"""
                  <li class="list-group-item mb-2">
                        <div class="content">
                          <strong>{c.user.name}</strong>
                          <p>{c.msg}</p>
                  """
                
                  if request.session.get('customer'):
                        html +=f"""      
                              <div class="mt-1 replay" style="display:none;" id="replay-{c.id}">
                                    <textarea class="form-control" name="replay"></textarea>
                                    <button class="btn btn-sm btn-success mt-1" onclick="sendComment({c.id})">Replay</button>
                              </div>
                        """
                  html +=f"""      
                       <div id="li-{c.id}"></div>
                  </li>
                  """
            else:
                  if request.session.get('customer'):
                        if c.status != "1" and request.session.get('customer')['id'] == c.user_id:
                              html += f"""
                              <li class="list-group-item mb-2">
                                    <div class="content">
                                          <strong>{c.user.name}</strong>
                                          <p>Your comment send for approval.</p> 
                                    </div>

                              </li>
                              """

                        else:
                              if c.status == "1":
                                    html += f"""
                                    <li class="list-group-item mb-2">
                                          <div class="content">
                                                <strong>{c.user.name}</strong>
                                                <p>{c.msg}</p>
                                                <button class="btn btn-sm btn-danger" onclick="onReplay({c.id})">Replay</button>
                                                <button class="btn btn-sm btn-dark" onclick="loadData({c.id})">More</button>
                                          </div>
                                          <div id="li-{c.id}"></div>
                                    
                                          <div class="mt-1 replay" style="display:none;" id="replay-{c.id}">
                                                <textarea class="form-control" name="replay"></textarea>
                                                <button class="btn btn-sm btn-success mt-1" onclick="sendComment({c.id})">Replay</button>
                                          </div>
                                    </li>
                                    """


                  else:
                        
                        if c.status == "1":
                              html += f"""
                              <li class="list-group-item mb-2">
                                    <div class="content">
                                    <strong>{c.user.name}</strong>
                                    <p>{c.msg}</p>
                                    <button class="btn btn-sm btn-dark" onclick="loadData({c.id})">More</button>
                                    </div>
                                    <div id="li-{c.id}"></div>
                              </li>
                              """
                 
      if parentId:
         html +='</ul>'    
      return JsonResponse({
      "success": True,
      "comment":html,
      "parentId":parentId,
      "isComment":isComment
      }, status=200)
    else:
      baseUrl = settings.BASE_URL
      trands=Trand.objects.using('movieplanet').select_related('post').filter(status=1)[0:5]
      context = {
         "link":Link,
         "baseUrl":baseUrl,
         "post":data,
         "Trands":trands
      }
      return render(request,"movieplanet/detail.html",context)

def menubar(request,*args,**kwargs):
      try:
            menu = Menu.objects.using('movieplanet').filter(status=1).all()
            html = ''
            for m in menu:
                if m.menuId is None:
                   if m.type == 2:
                        html += (f'<li><button class="nav-link dropdown-btn" data-dropdown="dropdown{m.id}" aria-haspopup="true" aria-expanded="false" aria-label="discover">{m.name}<i class="bx bx-chevron-down" aria-hidden="true"></i></button>'
                                    f'{menuBarLoop(menu,m.id)}'
                                    f'</li>')
                   elif m.type == 1:  
                        html += (f'<li><a class="nav-link dropdown-link dropdown-btn" data-dropdown="dropdown{m.id}" href="{ settings.BASE_URL }{m.link}" aria-haspopup="true" aria-expanded="false">{m.name}</a></li>')
                  
            return JsonResponse({"status":True,"Menus":html})
      except Exception as e:
            return JsonResponse({"status":False,"error": str(e)}, status=500)

def menuBarLoop(Menus=[],MenuId=None,IsLoop=None):
   check = False
   menu = f'<div id="dropdown{MenuId}" class="dropdown"><ul role="menu">'
   arrow = ''
   if IsLoop:
      menu = f'<div id="dropdown{MenuId}" class="dropdown loopMenu"><ul role="menu">'
      arrow = '<i class="bx bx-chevron-down" aria-hidden="true"></i>'
   for m in Menus:
      check = True
      if m.menuId and int(m.menuId) == int(MenuId):
            if m.type == 2:
                  menu += (f'<li><button class="nav-link dropdown-btn" data-dropdown="dropdown{m.id}" aria-haspopup="true" aria-expanded="false" aria-label="discover">{m.name}<i class="bx bx-chevron-down" aria-hidden="true"></i></button>'
                              f'{menuBarLoop(menu,m.id)}'
                              f'</li>')
            elif m.type == 1:  
                  menu += (f'<li><a class="nav-link dropdown-link dropdown-btn" data-dropdown="dropdown{m.id}" href="{ settings.BASE_URL }{m.link}" aria-haspopup="true" aria-expanded="false">{m.name}</a></li>')
                                 
   menu +='</ul></div>'
   if check:
      return menu
   else:    
      return ''


