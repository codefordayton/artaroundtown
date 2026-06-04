from django.views.generic import ListView, DetailView

from .models import Artist, Medium


class ArtistListView(ListView):
    model = Artist
    template_name = 'artists/artist_list.html'
    context_object_name = 'artists'

    def get_queryset(self):
        qs = Artist.objects.filter(is_active=True).prefetch_related('mediums')
        medium_slug = self.request.GET.get('medium')
        if medium_slug:
            qs = qs.filter(mediums__slug=medium_slug)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['mediums'] = Medium.objects.all()
        ctx['selected_medium'] = self.request.GET.get('medium', '')
        return ctx


class ArtistDetailView(DetailView):
    model = Artist
    template_name = 'artists/artist_detail.html'
    context_object_name = 'artist'
    queryset = Artist.objects.filter(is_active=True).prefetch_related('mediums')
