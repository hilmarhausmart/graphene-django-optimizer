import uuid

from django.db import models


class Catalogue(models.Model):
    name = models.CharField(max_length=100, blank=True)


class Item(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4)
    name = models.CharField(max_length=100, blank=True)
    parent = models.ForeignKey('Item', on_delete=models.SET_NULL, null=True, related_name='children')
    catalogue = models.ForeignKey('Catalogue', on_delete=models.PROTECT, null=True, related_name='items')
    item = models.ForeignKey('Item', on_delete=models.SET_NULL, null=True)

    item_type = 'simple'

    @property
    def title(self):
        return self.name

    @property
    def unoptimized_title(self):
        return self.title

    def all_children(self):
        return self.children.all()


class DetailedItem(Item):
    detail = models.TextField(null=True)
    item_type = models.CharField(max_length=100, null=True)


class RelatedItem(Item):
    related_items = models.ManyToManyField(Item)


class ExtraDetailedItem(DetailedItem):
    extra_detail = models.TextField()


class UnrelatedModel(models.Model):
    detail = models.TextField(null=True)
