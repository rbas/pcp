# -*- coding: utf-8 -*-

from django.contrib.auth.models import User as user
from django.db import models
from django.forms import ModelForm
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from wsgiadmin.keystore.tools import *
from wsgiadmin.requests.tools import request_raw


class form_user(ModelForm):
    class Meta:
        model = user
        exclude = ("password", "is_staff", "is_superuser", "last_login", "date_joined", "groups", "user_permissions")


class Machine(models.Model):
    name = models.CharField(_(u"Název serveru"), max_length=50)
    domain = models.CharField(_(u"Doménová adresa serveru"), max_length=50)
    ip = models.CharField(_(u"IP adresa serveru"), max_length=50)
    ipv6 = models.CharField(_(u"IPv6 adresa serveru"), max_length=50, blank=True)

    #web		= models.BooleanField(_(u"Provoz webu (společně s SSH)"),default=True)
    #postgres	= models.BooleanField(_(u"Provoz Postgresql"),default=True)
    #mysql		= models.BooleanField(_(u"Provoz mysql"),default=True)
    #email		= models.BooleanField(_(u"Provoz e-mailů"),default=True)

    def __repr__(self):
        return "<Machine %s>" % self.name

    def __unicode__(self):
        return "%s" % (self.name)


class form_machine(ModelForm):
    class Meta:
        model = Machine


class Address(models.Model):
    # sídlo
    company = models.CharField(_(u"Jméno společnosti"), max_length=250, blank=True)

    residency_name = models.CharField(_(u"Jméno a příjmení"), max_length=250, blank=True)
    residency_street = models.CharField(_(u"Ulice a č.p."), max_length=250)
    residency_city = models.CharField(_(u"Město"), max_length=250)
    residency_city_num = models.CharField(_(u"PSČ"), max_length=6)
    residency_ic = models.CharField(_(u"IČ"), max_length=50, blank=True)
    residency_dic = models.CharField(_(u"DIČ"), max_length=50, blank=True)
    residency_email = models.CharField(_(u"Email"), max_length=250)
    residency_phone = models.CharField(_(u"Telefon/Mobil"), max_length=30)
    # fakturační
    different = models.BooleanField(_(u"Odlišná od sídla?"), blank=True, default=False)
    invoice_name = models.CharField(_(u"Jméno a příjmení"), max_length=250, blank=True)
    invoice_street = models.CharField(_(u"Ulice a č.p."), max_length=250, blank=True)
    invoice_city = models.CharField(_(u"Město"), max_length=250, blank=True)
    invoice_city_num = models.CharField(_(u"PSČ"), max_length=6, blank=True)
    invoice_email = models.CharField(_(u"Email"), max_length=250, blank=True)
    invoice_phone = models.CharField(_(u"Telefon/Mobil"), max_length=30, blank=True)

    note = models.TextField(_(u"Poznámka"), blank=True)

    def __repr__(self):
        return "<Address %s>" % self.residency_name

    def __unicode__(self):
        if self.company:
            return "%s - %s" % (self.residency_name, self.company)
        else:
            return "%s" % (self.residency_name)

    def getName(self):
        if self.company:
            return "%s - %s" % (self.residency_name, self.company)
        else:
            return "%s" % (self.residency_name)

    def getInvoiceAddress(self):
        addr = ""
        if not self.different:
            if len(self.company) == 0:
                addr += self.residency_name + "\n"
            else:
                addr += self.company + "\n"
            addr += self.residency_street + "\n"
            addr += self.residency_city_num
            addr += "  " + self.residency_city + "\n"
        else:
            if len(self.company) == 0:
                addr += self.invoice_name + "\n"
            else:
                addr += self.company + "\n"
            addr += self.invoice_street + "\n"
            addr += self.invoice_city_num
            addr += "  " + self.invoice_city + "\n"

        addr += "\n"
        tail = ""
        if self.id == 1: tail = "Neplátce DPH"
        if len(self.residency_ic) > 0: addr += "IČ" + ": " + self.residency_ic + "   " + tail + "\n"
        if len(self.residency_dic) > 0: addr += "DIČ" + ": " + self.residency_dic + "\n"

        return str(addr)

    def getInvoiceContact(self):
        contact = ""
        if not self.different:
            contact += "Telefon" + ": " + self.residency_phone + "\n"
            contact += "Email" + ": " + self.residency_email + "\n"
        else:
            contact += "Telefon" + ": " + self.invoice_phone + "\n"
            contact += "Email" + ": " + self.invoice_email + "\n"

        return str(contact)

    class Meta:
        verbose_name = _(u"Adresa")
        verbose_name_plural = _(u"Adresy")


class form_address(ModelForm):
    class Meta:
        model = Address


class formPassword(forms.Form):
    password1 = forms.CharField(label=_(u"Heslo poprvé"), widget=forms.PasswordInput(render_value=False))
    password2 = forms.CharField(label=_(u"Heslo pro kontrolu"), widget=forms.PasswordInput(render_value=False))

    def clean_password1(self):
        if not "password1" in self.cleaned_data: raise forms.ValidationError(
            _(u"Je potřeba vyplnit heslo do obou políček"))
        if len(self.cleaned_data["password1"]) < 6: raise forms.ValidationError(_(u"Heslo musí mít alespoň 6 znaků"))
        return self.cleaned_data["password1"]

    def clean_password2(self):
        if not ("password1" in self.cleaned_data and "password2" in self.cleaned_data):
            raise forms.ValidationError(_(u"Je potřeba vyplnit obe pole pro kontrolu"))

        if self.cleaned_data["password1"] != self.cleaned_data["password2"]:
            raise forms.ValidationError(_(u"První heslo nesouhlasí s druhým"))

        return self.cleaned_data["password2"]


class Parms(models.Model):
    home = models.CharField(_(u"Home"), max_length=100)
    note = models.TextField(_(u"Poznámka"), blank=True)
    uid = models.IntegerField(_(u"UID"))
    gid = models.IntegerField(_(u"GID"))
    discount = models.IntegerField(_(u"Sleva"), default=0) # v procentech
    fee = models.IntegerField(_(u"Paušál"), default=0)
    currency = models.CharField(_("Měna"), max_length=20, choices=settings.CURRENCY, default="czk")
    enable = models.BooleanField(_("Stav účtu"), default=True)

    #address		= models.ForeignKey("address")
    address = models.OneToOneField(Address)
    web_machine = models.ForeignKey(Machine, related_name="web")
    mail_machine = models.ForeignKey(Machine, related_name="mail")
    mysql_machine = models.ForeignKey(Machine, related_name="mysql")
    pgsql_machine = models.ForeignKey(Machine, related_name="pgsql")

    user = models.OneToOneField(user, verbose_name=_('Uživatel'))

    def prefix(self):
        if len(self.user.username) > 3:
            return self.user.username[0:3]
        else:
            return self.user.username

    def dc(self):
        """Discount coeficient"""
        if 100 - self.discount > 0:
            return (100.0 - self.discount) / 100.0
        else:
            return 0.0

    def count_domains(self):
        return self.user.domain_set.count()

    def count_ftps(self):
        return self.user.ftp_set.count()

    def count_pgs(self):
        return self.user.pgsql_set.count()

    def count_mys(self):
        return self.user.mysqldb_set.count()

    def count_sites(self):
        return self.user.site_set.filter(removed=False).count()

    def count_emails(self):
        count = 0
        for domain in self.user.domain_set.all():
            count += domain.email_set.filter(remove=False).count()
        return count

    def home_size(self):
        size = kget("%s:homesize" % self.user.username)
        if size:
            return size_format(int(size))
        else:
            return _(u"Nezjištěno")

    def pay_for_sites(self):
        pay = 0.0
        for site in self.user.site_set.all():
            pay += site.pay()
        return pay

    def pay_total_day(self):
        return self.pay_for_sites()

    def pay_total_month(self):
        return self.pay_for_sites() * 30.0

    def installed(self):
        rr = request_raw(self.web_machine.ip)
        data = rr.run("cat /etc/passwd")["stdout"]
        users = []

        for line in [x.strip() for x in data.split("\n")]:
            line = line.split(":")
            users.append(line[0])

        return self.user.username in users

    def __repr__(self):
        return "<Config %s>" % self.user.username

    def __unicode__(self):
        return "%s" % (self.user.username)

    class Meta:
        verbose_name = _(u"Uživatel")
        verbose_name_plural = _(u"Uživatelé")


class form_parms(ModelForm):
    class Meta:
        model = Parms
        exclude = ("address", "user", "home", "uid", "gid")
