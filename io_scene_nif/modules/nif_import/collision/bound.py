"""This script contains classes to import collision objects."""

# ***** BEGIN LICENSE BLOCK *****
#
# Copyright © 2020, NIF File Format Library and Tools contributors.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials provided
#      with the distribution.
#
#    * Neither the name of the NIF File Format Library and Tools
#      project nor the names of its contributors may be used to endorse
#      or promote products derived from this software without specific
#      prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# ***** END LICENSE BLOCK *****
from pyffi.formats.nif import NifFormat

from io_scene_nif.modules.nif_import.collision import Collision
from io_scene_nif.modules.nif_import.object import Object


class Bound(Collision):

    def import_bounding_volume(self, bounding_volume):
        """Imports a NiCollisionData's bounding_volume """

        bvt = bounding_volume.collision_type
        # sphere
        if bvt == 0:
            return self.import_spherebv(bounding_volume.sphere)
        # box
        elif bvt == 1:
            return self.import_boxbv(bounding_volume.box)
        # capsule
        elif bvt == 2:
            return self.import_capsulebv(bounding_volume.capsule)
        # union - a bundle
        elif bvt == 4:
            volumes = []
            for sub_vol in bounding_volume.union.bounding_volumes:
                volumes.extend(self.import_bounding_volume(sub_vol))
            return volumes
        # don't support 5 Half Space for now
        return []

    def import_bounding_box(self, n_block):
        """Import a NiNode's bounding box or attached BSBound extra data."""
        if not n_block or not isinstance(n_block, NifFormat.NiNode):
            return []
        # we have a ninode with bounding box
        if n_block.has_bounding_box:
            b_name = 'Bounding Box'

            # Ninode's bbox behaves like a seperate mesh.
            # bounding_box center(n_block.bounding_box.translation) is relative to the bound_box
            minx = n_block.bounding_box.translation.x - n_block.translation.x - n_block.bounding_box.radius.x
            miny = n_block.bounding_box.translation.y - n_block.translation.y - n_block.bounding_box.radius.y
            minz = n_block.bounding_box.translation.z - n_block.translation.z - n_block.bounding_box.radius.z
            maxx = n_block.bounding_box.translation.x - n_block.translation.x + n_block.bounding_box.radius.x
            maxy = n_block.bounding_box.translation.y - n_block.translation.y + n_block.bounding_box.radius.y
            maxz = n_block.bounding_box.translation.z - n_block.translation.z + n_block.bounding_box.radius.z
            bbox_center = n_block.bounding_box.translation.as_list()

        # we may still have a BSBound extra data attached to this node
        else:
            for n_extra in n_block.get_extra_datas():
                if isinstance(n_extra, NifFormat.BSBound):
                    b_name = 'BSBound'
                    minx = n_extra.center.x - n_extra.dimensions.x
                    miny = n_extra.center.y - n_extra.dimensions.y
                    minz = n_extra.center.z - n_extra.dimensions.z
                    maxx = n_extra.center.x + n_extra.dimensions.x
                    maxy = n_extra.center.y + n_extra.dimensions.y
                    maxz = n_extra.center.z + n_extra.dimensions.z
                    bbox_center = n_extra.center.as_list()
                    break
            # none was found
            else:
                return []

        # create blender object
        b_obj = Object.box_from_extents(b_name, minx, maxx, miny, maxy, minz, maxz)
        # probably only on NiNodes with BB
        if hasattr(n_block, "flags"):
            b_obj.niftools.objectflags = n_block.flags
        b_obj.location = bbox_center
        self.set_b_collider(b_obj, "BOX", max(maxx, maxy, maxz))
        return [b_obj, ]

    def import_spherebv(self, sphere):
        r = sphere.radius
        c = sphere.center
        b_obj = Object.box_from_extents("sphere", -r, r, -r, r, -r, r)
        b_obj.location = (c.x, c.y, c.z)
        self.set_b_collider(b_obj, "SPHERE", r)
        return [b_obj]

    def import_boxbv(self, box):
        offset = box.center
        # ignore for now, seems to be a unity 3x3 matrix
        axes = box.axis
        x, y, z = box.extent
        b_obj = Object.box_from_extents("box", -x, x, -y, y, -z, z)
        b_obj.location = (offset.x, offset.y, offset.z)
        self.set_b_collider(b_obj, "BOX", (x + y + z) / 3)
        return [b_obj]

    def import_capsulebv(self, capsule):
        offset = capsule.center
        # always a normalized vector
        direction = capsule.origin
        # nb properly named in newer nif.xmls
        extent = capsule.unknown_float_1
        radius = capsule.unknown_float_2

        # positions of the box verts
        minx = miny = -radius
        maxx = maxy = +radius
        minz = -(extent + 2 * radius) / 2
        maxz = +(extent + 2 * radius) / 2

        # create blender object
        b_obj = Object.box_from_extents("capsule", minx, maxx, miny, maxy, minz, maxz)
        # apply transform in local space
        b_obj.matrix_local = self.center_origin_to_matrix(offset, direction)
        self.set_b_collider(b_obj, "CAPSULE", radius)
        return [b_obj]