from django.test import TestCase
from django.utils import timezone
from django.db import models
from apps.core.models.base import BaseModel, TimeStampedModel, SoftDeleteManager
from datetime import timedelta


class ConcreteBaseModel(BaseModel):
    """Concrete model for testing BaseModel"""
    name = models.CharField(max_length=100)


class ConcreteTimeStampedModel(TimeStampedModel):
    """Concrete model for testing TimeStampedModel"""
    name = models.CharField(max_length=100)


class BaseModelTest(TestCase):
    """Test cases for BaseModel abstract class"""
    
    def setUp(self):
        self.instance = ConcreteBaseModel.objects.create(name="Test Instance")
    
    def test_uuid_auto_generation(self):
        """Test that UUID is automatically generated"""
        self.assertIsNotNone(self.instance.uuid)
        self.assertEqual(len(str(self.instance.uuid)), 36)
    
    def test_uuid_is_unique(self):
        """Test that UUID is unique across instances"""
        instance2 = ConcreteBaseModel.objects.create(name="Test Instance 2")
        self.assertNotEqual(self.instance.uuid, instance2.uuid)
    
    def test_created_at_auto_set(self):
        """Test that created_at is automatically set"""
        self.assertIsNotNone(self.instance.created_at)
        self.assertLessEqual(self.instance.created_at, timezone.now())
    
    def test_updated_at_auto_updates(self):
        """Test that updated_at updates on save"""
        original_updated = self.instance.updated_at
        self.instance.name = "Updated Name"
        self.instance.save()
        self.assertGreater(self.instance.updated_at, original_updated)
    
    def test_is_active_default_true(self):
        """Test that is_active defaults to True"""
        self.assertTrue(self.instance.is_active)
    
    def test_soft_delete(self):
        """Test soft delete functionality"""
        self.instance.soft_delete()
        self.assertFalse(self.instance.is_active)
        
        # Should be excluded from default queryset
        self.assertFalse(ConcreteBaseModel.objects.filter(id=self.instance.id).exists())
        
        # Should be available in archived queryset
        self.assertTrue(ConcreteBaseModel.objects.archived().filter(id=self.instance.id).exists())
    
    def test_restore(self):
        """Test restore functionality"""
        self.instance.soft_delete()
        self.instance.restore()
        self.assertTrue(self.instance.is_active)
        self.assertTrue(ConcreteBaseModel.objects.filter(id=self.instance.id).exists())
    
    def test_is_deleted_property(self):
        """Test is_deleted property"""
        self.assertFalse(self.instance.is_deleted)
        self.instance.soft_delete()
        self.assertTrue(self.instance.is_deleted)
    
    def test_str_method(self):
        """Test string representation"""
        self.assertIn("ConcreteBaseModel", str(self.instance))
        self.assertIn(str(self.instance.uuid), str(self.instance))
    
    def test_ordering(self):
        """Test default ordering by -created_at"""
        instance1 = ConcreteBaseModel.objects.create(name="First")
        instance2 = ConcreteBaseModel.objects.create(name="Second")
        instance3 = ConcreteBaseModel.objects.create(name="Third")
        
        # Give time difference
        instance1.created_at = timezone.now() - timedelta(days=2)
        instance1.save()
        instance2.created_at = timezone.now() - timedelta(days=1)
        instance2.save()
        
        queryset = ConcreteBaseModel.objects.all()
        self.assertEqual(queryset[0].id, instance3.id)  # Most recent first
        self.assertEqual(queryset[2].id, instance1.id)  # Oldest last
    
    def test_indexes_created(self):
        """Test that indexes are created properly"""
        indexes = ConcreteBaseModel._meta.indexes
        index_names = [idx.name for idx in indexes if hasattr(idx, 'name')]
        self.assertTrue(any('uuid' in str(idx) for idx in indexes))
        self.assertTrue(any('created_at' in str(idx) for idx in indexes))


class TimeStampedModelTest(TestCase):
    """Test cases for TimeStampedModel abstract class"""
    
    def setUp(self):
        self.instance = ConcreteTimeStampedModel.objects.create(name="Test")
    
    def test_created_at_auto_set(self):
        """Test created_at is auto-set"""
        self.assertIsNotNone(self.instance.created_at)
    
    def test_updated_at_auto_updates(self):
        """Test updated_at updates"""
        original = self.instance.updated_at
        self.instance.name = "Updated"
        self.instance.save()
        self.assertGreater(self.instance.updated_at, original)
    
    def test_no_uuid_field(self):
        """Test that TimeStampedModel doesn't have UUID"""
        self.assertFalse(hasattr(self.instance, 'uuid'))
    
    def test_no_soft_delete(self):
        """Test that TimeStampedModel doesn't have soft delete"""
        self.assertFalse(hasattr(self.instance, 'is_active'))
        self.assertFalse(hasattr(self.instance, 'soft_delete'))


class SoftDeleteManagerTest(TestCase):
    """Test cases for SoftDeleteManager"""
    
    def setUp(self):
        self.active1 = ConcreteBaseModel.objects.create(name="Active 1")
        self.active2 = ConcreteBaseModel.objects.create(name="Active 2")
        self.deleted = ConcreteBaseModel.objects.create(name="Deleted")
        self.deleted.soft_delete()
    
    def test_default_queryset_excludes_deleted(self):
        """Test that default manager excludes soft-deleted records"""
        queryset = ConcreteBaseModel.objects.all()
        self.assertEqual(queryset.count(), 2)
        self.assertNotIn(self.deleted, queryset)
    
    def test_active_method(self):
        """Test active() method returns only active records"""
        queryset = ConcreteBaseModel.objects.active()
        self.assertEqual(queryset.count(), 2)
    
    def test_archived_method(self):
        """Test archived() method returns only deleted records"""
        queryset = ConcreteBaseModel.objects.archived()
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().id, self.deleted.id)
    
    def test_all_including_archived_method(self):
        """Test all_including_archived() returns all records"""
        queryset = ConcreteBaseModel.objects.all_including_archived()
        self.assertEqual(queryset.count(), 3)