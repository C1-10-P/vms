import uuid
from django.db import models
from django.utils import timezone
from django.contrib.postgres.indexes import GinIndex

class BaseModel(models.Model):
    """
    Abstract base model with common fields for all models.
    Provides UUID, timestamps, and soft delete functionality.
    """
    uuid = models.UUIDField(
        default=uuid.uuid4, 
        unique=True, 
        editable=False,
        db_index=True,
        help_text="Public unique identifier"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when record was last updated"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Soft delete flag - False means record is archived"
    )
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['uuid', 'is_active']),
            models.Index(fields=['created_at', 'is_active']),
        ]
    
    def soft_delete(self):
        """Soft delete the record"""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])
    
    def restore(self):
        """Restore a soft-deleted record"""
        self.is_active = True
        self.save(update_fields=['is_active', 'updated_at'])
    
    @property
    def is_deleted(self):
        """Check if record is soft deleted"""
        return not self.is_active
    
    def __str__(self):
        return f"{self.__class__.__name__}-{self.uuid}"


class TimeStampedModel(models.Model):
    """
    Abstract model for time tracking only (no UUID).
    Used for log tables and high-volume transaction tables.
    """
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['created_at']),
        ]


class SoftDeleteManager(models.Manager):
    """
    Manager that excludes soft-deleted records by default.
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)
    
    def active(self):
        """Get active records only"""
        return self.get_queryset()
    
    def archived(self):
        """Get archived (soft-deleted) records only"""
        return super().get_queryset().filter(is_active=False)
    
    def all_including_archived(self):
        """Get all records including archived"""
        return super().get_queryset()


class ActiveManager(SoftDeleteManager):
    """Alias for SoftDeleteManager"""
    pass