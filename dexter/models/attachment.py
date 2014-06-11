import datetime
import io
from cStringIO import StringIO

from sqlalchemy import (
    Table,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
    Index,
    )
from sqlalchemy.orm import relationship, backref
from sqlalchemy_imageattach.entity import Image, image_attachment
from sqlalchemy_imageattach.context import current_store
from werkzeug.utils import secure_filename
from wand.image import Image as WandImage

from .support import db


import logging

# mimetypes we accept
MIMETYPES = set("image/png image/jpeg image/gif application/pdf".split())
PDF = "application/pdf"


class DocumentAttachment(db.Model):
    """
    An attachment for a document.

    Some attachments might not be associated with a document. This happens when a new
    document is being added and we don't yet have a document id. When the document is
    fully created the attachment ids will be included in the request and linked to the
    document.
    
    We'll clean up stranded attachments periodically.
    """
    __tablename__ = "attachments"
    log = logging.getLogger(__name__)

    id        = Column(Integer, primary_key=True)

    filename  = Column(String(256), nullable=False)
    mimetype  = Column(String(256), nullable=False)
    document_id = Column(Integer, ForeignKey('documents.id'), index=True)

    created_by_user_id = Column(Integer, ForeignKey('users.id'), index=True)

    created_at   = Column(DateTime(timezone=True), index=True, unique=False, nullable=False, server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.current_timestamp())

    # Associations
    created_by  = relationship("User", foreign_keys=[created_by_user_id])
    image       = image_attachment("AttachmentImage", cascade='all, delete-orphan', passive_deletes=True)


    THUMBNAIL_HEIGHT = 100

    def generate_thumbnails(self):
        self.image.generate_thumbnail(height=self.THUMBNAIL_HEIGHT)


    def set_data(self, data):
        """ Set the data for this attachment from a file-like object. """
        if self.mimetype == PDF:
            if self.id is None:
                db.session.add(self)
                db.session.flush()

            # save pdf to s3
            current_store.put_file(data, 'document-attachment', self.id, 0, 0, self.mimetype, False)
            data.seek(0)

            # convert to an image for use with thumbnails
            self.log.info("Converting PDF to image")
            with WandImage(file=data, resolution=300) as img:
                img.format = 'png'
                data = StringIO()
                img.save(file=data)
                data.seek(0)
            self.log.info("Converted")

        self.image.from_file(data)
        db.session.flush()
        self.generate_thumbnails()


    @property
    def thumbnail_url(self):
        return self.image.find_thumbnail(height=self.THUMBNAIL_HEIGHT).locate()

    @property
    def preview_url(self):
        return self.image.original.locate()

    @property
    def download_url(self):
        if self.mimetype == PDF:
            return current_store.get_url('document-attachment', self.id, 0, 0, self.mimetype)

        return self.image.original.locate()


    def size_str(self):
        return '%d,%d' % self.image.original.size


    def to_json(self):
        return {
            'id': self.id,
            'url': self.preview_url,
            'thumbnail_url': self.thumbnail_url,
            'download_url': self.download_url,
            'size': self.size_str(),
        }


    @classmethod
    def is_acceptable(cls, upload):
        """
        Is this `werkzeug.FileStorage` object a valid upload?
        """
        return upload.mimetype in MIMETYPES


    @classmethod
    def from_upload(cls, upload, user=None, document=None):
        """
        Create a new attachment from an uploaded file, a `werkzeug.FileStorage` object.
        """
        attachment = DocumentAttachment()
        attachment.document = document
        attachment.filename = secure_filename(upload.filename)
        attachment.mimetype = upload.mimetype

        if user and user.is_authenticated():
            attachment.created_by = user

        # set the data and generate thumbnails
        attachment.set_data(upload.stream)

        return attachment
        

class AttachmentImage(db.Model, Image):
    __tablename__ = "attachment_images"

    id            = Column(Integer, primary_key=True)
    width         = Column('width', Integer)
    height        = Column('height', Integer)
    attachment_id = Column(Integer, ForeignKey('attachments.id'), index=True)

Index('attachment_images_w_h_id_ix', AttachmentImage.width, AttachmentImage.height, AttachmentImage.attachment_id, unique=True)
