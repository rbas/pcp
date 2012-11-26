from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import ListView, TemplateView, CreateView
from wsgiadmin.apps.forms import AppForm, AppStaticForm, AppPHPForm, AppNativeForm, AppProxyForm, AppPythonForm
from wsgiadmin.apps.models import App
from wsgiadmin.apps.apps import PythonApp, AppObject
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext as __
from django.contrib import messages


class AppsListView(ListView):
    menu_active = "apps"
    model = App
    template_name = "apps.html"

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.session.get('switched_user', request.user)
        return super(AppsListView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super(AppsListView, self).get_queryset()
        queryset = queryset.filter(user=self.user)
        return queryset

    def get_context_data(self, **kwargs):
        context = super(AppsListView, self).get_context_data(**kwargs)
        context['menu_active'] = self.menu_active
        context['u'] = self.user
        context['superuser'] = self.request.user
        return context


class AppDetailView(TemplateView):
    model = App
    menu_active = "apps"
    template_name = "app_info.html"

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.session.get('switched_user', request.user)
        return super(AppDetailView, self).dispatch(request, *args, **kwargs)

    def get_object(self):
        app_id = self.kwargs.get("app_id")
        if not app_id:
            raise Http404
        app = self.model.objects.get(id=app_id, user=self.user)
        if app.app_type == "python":
            app = PythonApp.objects.get(id=app.id)
        else:
            app = AppObject.objects.get(id=app.id)
        return app

    def get_context_data(self, **kwargs):
        context = super(AppDetailView, self).get_context_data(**kwargs)
        context['menu_active'] = self.menu_active
        context['u'] = self.user
        context['superuser'] = self.request.user
        context['app'] = self.get_object()
        return context


class AppParametersView(TemplateView):
    menu_active = "apps"
    app_type = None
    template_name = "universal.html"

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = self.get_form()(request.POST)
        if form.is_valid():
            app = self.get_object()
            parms = {}
            for field in form.cleaned_data:
                if field == "domains":
                    app.domains = form.cleaned_data[field]
                elif field == "password":
                    continue
                else:
                    parms[field] = form.cleaned_data[field]
            app.parameters = parms
            app.save()

            # communication with server
            if not app.installed:
                app.install()
            app.update()
            if app.app_type == "python":
                app.restart()
            if form.cleaned_data["password"]:
                app.passwd(form.cleaned_data["password"])
            app.commit()

            messages.add_message(request, messages.SUCCESS, _('Changes has been saved.'))
            return HttpResponseRedirect(reverse("apps_list"))
        context["form"] = form
        return self.render_to_response(context)

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = self.get_form()(initial=self.get_initial())
        context["form"] = form
        return self.render_to_response(context)

    def get_autocomplete_list(self):
        return []

    def get_form(self):
        if self.app_type == "static":
            form = AppStaticForm
        elif self.app_type == "php":
            form = AppPHPForm
        elif self.app_type == "python":
            form = AppPythonForm
        elif self.app_type == "native":
            form = AppNativeForm
        elif self.app_type == "proxy":
            form = AppProxyForm
        else:
            raise Http404
        form.this_app = self.get_object()
        return form

    def get_initial(self):
        initial = {"domains": self.get_object().domains}
        initial.update(self.get_object().parameters)
        return initial

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.session.get('switched_user', request.user)
        return super(AppParametersView, self).dispatch(request, *args, **kwargs)

    def get_object(self):
        app_id = self.kwargs.get("app_id")
        if not app_id:
            raise Http404
        app = self.user.app_set.get(id=app_id)
        if app.app_type == "python":
            app = PythonApp.objects.get(id=app.id)
        else:
            app = AppObject.objects.get(id=app.id)
        return app

    def get_context_data(self, **kwargs):
        context = super(AppParametersView, self).get_context_data(**kwargs)
        context['menu_active'] = self.menu_active
        context['u'] = self.user
        context['superuser'] = self.request.user
        context['app'] = self.get_object()
        context["title"] = __("Settings of the %s app") % self.get_object().name
        context['form'] = self.get_form()
        context['autocomplete_list'] = self.get_autocomplete_list()
        return context


class AppCreateView(CreateView):
    form_class = AppForm
    app_type = None
    template_name = "universal.html"
    model = App
    menu_active = "apps"

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.session.get('switched_user', request.user)
        return super(AppCreateView, self).dispatch(request, *args, **kwargs)

    def get_success_url(self):
        if self.app_type == "static":
            return reverse("app_params_static", kwargs={"app_id": self.object.id})
        elif self.app_type == "php":
            return reverse("app_params_php", kwargs={"app_id": self.object.id})
        elif self.app_type == "python":
            return reverse("app_params_python", kwargs={"app_id": self.object.id})
        elif self.app_type == "native":
            return reverse("app_params_native", kwargs={"app_id": self.object.id})
        elif self.app_type == "proxy":
            return reverse("app_params_proxy", kwargs={"app_id": self.object.id})
        else:
            return reverse("apps_list")

    def form_valid(self, form):
        success_url = super(AppCreateView, self).form_valid(form)
        self.object.user = self.user
        self.object.app_type = self.app_type
        self.object.save()
        return success_url

    def get_context_data(self, **kwargs):
        context = super(AppCreateView, self).get_context_data(**kwargs)
        context['menu_active'] = self.menu_active
        context['u'] = self.user
        context['superuser'] = self.request.user
        return context


@login_required()
def app_rm(request):
    user = request.session.get('switched_user', request.user)
    superuser = request.user

    app_id = int(request.GET.get("app_id"))
    app = get_object_or_404(user.app_set, id=app_id)
    if app.app_type == "python":
        app = PythonApp.objects.get(id=app.id)
    else:
        app = AppObject.objects.get(id=app.id)
    app.uninstall()
    app.commit()
    app.delete()
    messages.add_message(request, messages.SUCCESS, _('App has been removed'))
    return HttpResponseRedirect(reverse("apps_list"))


@login_required()
def app_restart(request):
    user = request.session.get('switched_user', request.user)
    superuser = request.user

    app_id = int(request.GET.get("app_id"))
    app = get_object_or_404(user.app_set, id=app_id)
    if app.app_type == "python":
        app = PythonApp.objects.get(id=app.id)
        app.update()
        app.restart()
        app.commit()
    messages.add_message(request, messages.SUCCESS, _('App has been restarted'))
    return HttpResponseRedirect(reverse("apps_list"))
