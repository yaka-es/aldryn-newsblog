# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from aldryn_apphooks_config.admin import BaseAppHookConfig, ModelAppHookConfig
from aldryn_people.models import Person
from aldryn_translation_tools.admin import AllTranslationsMixin
from cms.admin.placeholderadmin import FrontendEditableAdminMixin
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from parler.admin import TranslatableAdmin
from parler.forms import TranslatableModelForm

from djangocms_publisher.contrib.parler.admin import PublisherParlerAdminMixin
from djangocms_publisher.contrib.parler.utils import \
    publisher_translation_states_admin_field_names
from . import models

from cms.admin.placeholderadmin import PlaceholderAdminMixin


def make_published(modeladmin, request, queryset):
    queryset.update(publisher_is_published_version=True)


make_published.short_description = _(
    "Mark selected articles as published")


def make_unpublished(modeladmin, request, queryset):
    queryset.update(publisher_is_published_version=False)


make_unpublished.short_description = _(
    "Mark selected articles as not published")


def make_featured(modeladmin, request, queryset):
    queryset.update(is_featured=True)


make_featured.short_description = _(
    "Mark selected articles as featured")


def make_not_featured(modeladmin, request, queryset):
    queryset.update(is_featured=False)


make_not_featured.short_description = _(
    "Mark selected articles as not featured")


class ArticleAdminForm(TranslatableModelForm):

    class Meta:
        model = models.Article
        fields = [
            'app_config',
            'categories',
            'featured_image',
            'is_featured',
            # 'is_published',
            'lead_in',
            'meta_description',
            'meta_keywords',
            'meta_title',
            'owner',
            'related',
            'slug',
            'tags',
            'title',
        ]

    def __init__(self, *args, **kwargs):
        super(ArticleAdminForm, self).__init__(*args, **kwargs)

        qs = models.Article.objects
        if self.instance.app_config_id:
            qs = models.Article.objects.filter(
                app_config=self.instance.app_config)
        elif 'initial' in kwargs and 'app_config' in kwargs['initial']:
            qs = models.Article.objects.filter(
                app_config=kwargs['initial']['app_config'])

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if 'related' in self.fields:
            self.fields['related'].queryset = qs

        # Don't allow app_configs to be added here. The correct way to add an
        # apphook-config is to create an apphook on a cms Page.
        if 'app_config' in self.fields:
            self.fields['app_config'].widget.can_add_related = False
        # Don't allow related articles to be added here.
        # doesn't makes much sense to add articles from another article other
        # than save and add another.
        if ('related' in self.fields and
                hasattr(self.fields['related'], 'widget')):
            self.fields['related'].widget.can_add_related = False


class ArticleAdmin(
    PublisherParlerAdminMixin,
    AllTranslationsMixin,
    PlaceholderAdminMixin,
    FrontendEditableAdminMixin,
    ModelAppHookConfig,
    TranslatableAdmin
):
    form = ArticleAdminForm
    list_display = (
        'title',
        'app_config',
        'is_featured',
    ) + tuple(publisher_translation_states_admin_field_names())
    list_filter = [
        'app_config',
        'categories',
        'is_featured',
        'app_config',
    ]
    search_fields = (
        'translations__title',
        'publisher_published_version__translations__title',
        'publisher_draft_version__translations__title',
    )
    actions = (
        make_featured, make_not_featured,
        # FIXME: implement with djangocms-publisher
        # make_published, make_unpublished,
    )
    fieldsets = (
        (None, {
            'fields': (
                'title',
                'author',
                'publishing_date',
                # 'is_published',
                'is_featured',
                'featured_image',
                'lead_in',
            )
        }),
        (_('Meta Options'), {
            'classes': ('collapse',),
            'fields': (
                'slug',
                'meta_title',
                'meta_description',
                'meta_keywords',
            )
        }),
        (_('Advanced Settings'), {
            'classes': ('collapse',),
            'fields': (
                'tags',
                'categories',
                # FIXME: add related again. Right now it is making the whole changeview in admin display nothing at all.
                # 'related',
                'owner',
                'app_config',
            )
        }),
    )
    filter_horizontal = [
        'categories',
    ]
    readonly_fields = (
        'publisher_state',
        'publisher_translation_states',
        'publisher_is_published_version',
        'publisher_published_version',
        'publisher_deletion_requested',
        # 'is_published',
    )
    app_config_values = {
        'default_published': 'publisher_is_published_version',
    }
    app_config_selection_title = ''
    app_config_selection_desc = ''

    def get_changelist(self, request, **kwargs):
        # FIXME: create a helper in djangocms-publisher to make this easier
        # We override get_queryset on the ChangeList here because we want to
        # only show draft or published on the change list. But still allow
        # looking at either on the change_view.
        ChangeList = super(ArticleAdmin, self).get_changelist(request, **kwargs)

        class DraftOrLiveOnlyChangeList(ChangeList):
            def get_queryset(self, request):
                return (
                    super(DraftOrLiveOnlyChangeList, self)
                    .get_queryset(request)
                    .publisher_draft_or_published_only_prefer_published()
                )
        return DraftOrLiveOnlyChangeList

    def is_published(self, obj):
        return obj.publisher_is_published_version
    is_published.admin_order_field = 'publisher_is_published_version'
    is_published.short_description = 'pub'
    is_published.boolean = True

    def add_view(self, request, *args, **kwargs):
        data = request.GET.copy()
        try:
            person = Person.objects.get(user=request.user)
            data['author'] = person.pk
            request.GET = data
        except Person.DoesNotExist:
            pass

        data['owner'] = request.user.pk
        request.GET = data
        return super(ArticleAdmin, self).add_view(request, *args, **kwargs)


admin.site.register(models.Article, ArticleAdmin)


class NewsBlogConfigAdmin(
    AllTranslationsMixin,
    PlaceholderAdminMixin,
    BaseAppHookConfig,
    TranslatableAdmin
):
    def get_config_fields(self):
        return (
            'app_title', 'permalink_type', 'non_permalink_handling',
            'template_prefix', 'paginate_by', 'pagination_pages_start',
            'pagination_pages_visible', 'exclude_featured',
            'create_authors', 'search_indexed', 'config.default_published',
        )


admin.site.register(models.NewsBlogConfig, NewsBlogConfigAdmin)
