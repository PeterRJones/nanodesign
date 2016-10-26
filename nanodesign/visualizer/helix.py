#!/usr/bin/env python
""" This module is used to interactively visualize a virtual helix of a DNA model. 

    A virtual helix of a DNA nanodesign is an abstraction used to represent a potential helix in a DNA design.
    It is conceptualized as container for bases contributed by either the scaffold or staple strands that 
    form a DNA double helix. This helix may have interruptions or have segments that are single-stranded. 
    Virtual helices represent the rows in a caDNAno diagram. 

    The portion of a virtual helix containing double-stranded DNA is visualized as a transparent cylinder. 
    The base positions, base coordinates and strands associated with a virtual helix are visualized using several 
    representations:  

        coordinates - The positons of the helix bases are displayed as spheres connected by lines. 
        frames - The coodinates frames of the helix bases are displayed as an axis with an arrowhead on the helix
            axis. 
        crossovers - Crossovers are displayed as an arrow placed at the helix base and pointing to the
            crossover helix.
        domains - Helix domains are displayed as solid cylinders.
        geometry - The double-stranded DNA regions are displayed as transparent cylinders.
        nodes - The approximate position of DNA P atoms are displayed as spheres connected by lines.
        strands - The strands passing through the helix are displayed as a continuous line with arrows.
"""
import logging
import os
import sys
import numpy as np
from .geometry import VisGeometryCylinder,VisGeometryPath,VisGeometryAxes,VisGeometryLines,VisGeometrySymbols
from .strand import VisStrand

class VisHelixRepType:
    """ This class defines the helix visualization representation types. """
    UNKNOWN = 'unknown'
    BASE_POSITIONS    = 'base_positions'
    COORDINATES       = 'coordinates'
    COORDINATE_FRAMES = 'frames'
    DESIGN_CROSSOVERS = 'design_crossovers'
    DOMAINS           = 'domains'
    GEOMETRY          = 'geometry'
    INSERTS_DELETES   = 'inserts_deletes'
    STRANDS           = 'strands'

class VisHelix(object):
    """ This class is used to visualize a virtual helix from a DNA design.

        Attributes:
            color (List[float]): The default color of the geometry for a representation. 
            dna_structure (DnaStructure): The dna structure derived from a DNA design.
            graphics (VisGraphics): The VisGraphics object.
            id (int): The helix id. This is currently set to the caDNAno vhelix number.
            name (String): The string representation of the helix id.
            representations (Dict[List[VisGeometry]): The dictionary storing the list of geometry for a representation.
            vhelix (DnaStructureHelix): The structure helix from a region in a DNA structure. This object contains
                all the data needed to visualize a virtual helix.
    """
    def __init__(self, graphics, dna_structure, helix):
        """ Initialize a VisHelix object.

            Arguments:
                graphics (VisGraphics): The VisGraphics object.
                dna_structure (DnaStructure): The dna structure derived from a DNA design.
                helix (DnaStructureHelix): The structure helix from a region in a DNA structure. 
        """
        self.id = helix.lattice_num
        self.name = str(helix.lattice_num)
        self.graphics = graphics
        self.dna_structure = dna_structure
        self.vhelix = helix
        self.strand_ids = set()
        self.representations = {}
        self.color = [0.6,0.6,0.6,0.5]
        self._logger = self._setup_logging()
        # Set the methods to create geometry for the different representations.
        self.create_rep_methods = { 
            VisHelixRepType.COORDINATE_FRAMES : self.create_frames_rep, 
            VisHelixRepType.COORDINATES       : self.create_coords_rep,
            VisHelixRepType.DESIGN_CROSSOVERS : self.create_crossovers_rep,
            VisHelixRepType.DOMAINS           : self.create_domains_rep,
            VisHelixRepType.GEOMETRY          : self.create_geometry_rep,
            VisHelixRepType.INSERTS_DELETES   : self.create_inserts_deletes_rep,
            VisHelixRepType.BASE_POSITIONS    : self.create_base_positions_rep,
            VisHelixRepType.STRANDS           : self.create_strands_rep
        }

    def _setup_logging(self):
        """ Set up logging. """
        logger = logging.getLogger(__name__ + ":" + self.name)
        logger.setLevel(logging.INFO)
        # Create console handler and set format.
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(name)s] %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        return logger

    def get_boundaries(self):
        """ Get the start-end base positions of regions of dsDNA. """
        num_axis_nodes = len(self.vhelix.helix_axis_coords)

        # Get paired bases. 
        boundary_bases = []
        start_base = None
        end_base = None
        for base in self.vhelix.staple_base_list:
            if base.across == None: 
                if start_base != None:
                    boundary_bases.append((start_base,end_base))
                    start_base = None
                    end_base = None
                #__if start_base != None
            else:
                if start_base == None:
                    start_base = base
                    #self._logger.info("Start base %d" % start_base.p) 
                else:
                    end_base = base
                #__if start_base == None
        #__for base in self.vhelix.staple_base_list
        if end_base != None:
            boundary_bases.append((start_base,end_base))

        # Create pairs of points for the boudary bases.
        boundary_points = []
        for paired_bases in boundary_bases: 
            start_base = paired_bases[0]
            end_base = paired_bases[1]
            boundary_points.append((start_base.coordinates,end_base.coordinates))
        #__for paired_bases in boundary_bases
        return boundary_points

    def print_info(self):
        """ Print helix information. """
        self._logger.info("Polarity %s " % (str(self.vhelix.scaffold_polarity)))
        self._logger.info("Number of domains %d " % (len(self.vhelix.get_domain_ids())))
        if not self.strand_ids:
            domain_list = self.dna_structure.domain_list
            domain_ids = self.vhelix.get_domain_ids()
            for id in domain_ids:
                domain = domain_list[id]
                if domain.strand.id not in self.strand_ids:
                    self.strand_ids.add(domain.strand.id)
        #__if not self.strand_ids
        self._logger.info("Number of strands %d " % (len(self.strand_ids)))

    def show(self, rep, show, display=True):
        """ Show the geometry for the given representation.

            Arguments:
                rep (String): The representation name from VisHelixRepType.
                show (bool): If true then show the geometry for the representation, else hide it.
                dispay (bool): If true then redisplay all the graphics geometry.

            If the geometry for the representation has not been created then create and store it.
        """
        if rep not in self.representations:
            self.create_rep_methods[rep]()
        for geom in self.representations[rep]:
            geom.visible = show
        if display:
            self.graphics.display()

    def create_crossovers_rep(self):
        """ Create the geometry for the helix crossover representation. """
        #self._logger.setLevel(logging.DEBUG)
        self._logger.debug("Create crossover rep for helix num %d " % self.vhelix.lattice_num)
        dna_structure = self.dna_structure
        helix = self.vhelix
        helix_axis_coords = helix.helix_axis_coords
        lattice = dna_structure.lattice
        num_neigh = lattice.number_of_neighbors
        self._logger.debug("Number of lattice directions: %d " % num_neigh)
        helix_connectivity = helix.helix_connectivity
        self._logger.debug("Connections:") 
        s = 1.25
        verts = []
        entity_indexes = []
        n = 2
        crossover_data = []

        for connection in helix_connectivity:
            to_helix = connection.to_helix
            from_helix = connection.from_helix
            nindex = lattice.get_neighbor_index(helix.lattice_row, helix.lattice_col, 
                to_helix.lattice_row, to_helix.lattice_col)
            dir = connection.direction
            crossovers = connection.crossovers
            self._logger.debug("Helix  num %d  row %d  col %d " % (to_helix.lattice_num, to_helix.lattice_row,
                to_helix.lattice_col))
            self._logger.debug("    Nindex %d " % nindex)
            self._logger.debug("    Direction (%g %g %g) " % (dir[0], dir[1], dir[2]))
            self._logger.debug("    Number of crossovers %d " % len(crossovers))
            self._logger.debug("    Number of helix_axis_coords %d " % len(helix_axis_coords))

            for i in xrange(0,len(crossovers),1):
                crossover = crossovers[i]
                base = crossover.crossover_base
                pt1 = base.coordinates
                pt2 = pt1 + s*dir
                verts.append(pt1)
                verts.append(pt2)
                entity_indexes.append(n)
                n += 2
                crossover_data.append((from_helix.lattice_num,to_helix.lattice_num,base.p)) 
        #__for connection in helix_connectivity

        name = "HelixCrossovers:%s" % self.id
        arrows = False
        arrows = True
        geom = VisGeometryLines(name, verts, arrows)
        geom.line_width = 1.0 
        geom.color = [0.8,0.0,0.8,1]
        geom.entity_indexes = entity_indexes
        geom.selected_callback = self.select_crossover
        geom.data = crossover_data 
        self.representations[VisHelixRepType.DESIGN_CROSSOVERS] = [geom]
        self.graphics.add_render_geometry(geom)
        self._logger.setLevel(logging.INFO)

    def select_crossover(self, geom, index):
        """ Process helix crossover selection.

            Arguments:
                geom (VisGeometry): The geometry selected.
                index (int): The index into the geometry selected.
        """
        crossover_data = geom.data 
        crossover = crossover_data[index] 
        from_vh = crossover[0]
        to_vh = crossover[1]
        pos = crossover[2]
        self._logger.info("Selected Helix %s crossover. From vhelix %d to vhelix %d at position %d" % (self.name,
            from_vh, to_vh, pos))
        self.print_info()

    def create_geometry_rep(self):
        """ Create the geometry for the helix geometry representation. 

            The helix geometry is one or more cylinders representing regions containing double-stranded DNA.
        """
        point1 = self.vhelix.end_coordinates[0]
        point2 = self.vhelix.end_coordinates[1]
        radius = 1.0
        name = "HelixCylinder:%s" % self.id
        geom = VisGeometryCylinder(name, radius, point1, point2)
        geom.transparent = True
        geom.color = self.color
        geom.selected_callback = self.select_geometry
        self.representations[VisHelixRepType.GEOMETRY] = [geom]
        self.graphics.add_render_geometry(geom)

    def select_geometry(self, geom, index):
        """ Process helix geometry selection.

            Arguments:
                geom (VisGeometry): The geometry selected.
                index (int): The index into the geometry selected.
        """
        self._logger.info("Selected Helix %s geometry " % (self.name))
        self.print_info()

    def create_base_positions_rep(self):
        """ Create the geometry for the helix base positions representation. """
        points = self.vhelix.helix_axis_coords
        show_vertices = True
        name = "HelixNodes:%s" % self.id
        geom = VisGeometryPath(name, points, show_vertices)
        geom.color = [1.0, 0.5, 0.5, 1.0] 
        geom.line_width = 1.0
        geom.select_vertex = True
        geom.entity_indexes = range(0,len(points))
        geom.selected_callback = self.select_base_positions
        self.representations[VisHelixRepType.BASE_POSITIONS] = [geom]
        self.graphics.add_render_geometry(geom)

    def select_base_positions(self, geom, index):
        """ Process helix base positions selection.

            Arguments:
                geom (VisGeometry): The geometry selected.
                index (int): The index into the geometry selected.
        """
        coords = self.vhelix.helix_axis_coords[index]
        self._logger.info("Selected Helix %s node.  Location in helix %d  Coordinates (%g %g %g) " % (self.name, index+1, 
            coords[0], coords[1], coords[2]))
        self.print_info()

    def create_coords_rep(self):
        """ Create the geometry for the helix coordinates representation. 

            The coordinates representation is visualized by displaying the staple and scaffold P atoms as solid  
            spheres connected by lines.
        """
        staple_points = []
        for base in self.vhelix.staple_base_list:
            if base:
                staple_points.append(base.nt_coords)
        #__for id in base_ids
        scaffold_points = []
        for base in self.vhelix.scaffold_base_list:
            if base:
                scaffold_points.append(base.nt_coords)
        #__for id in base_ids

        # Create the scaffold geometry.
        show_vertices = True
        name = "HelixScaffoldCoords:%s" % self.id
        scaffold_geom = VisGeometryPath(name, scaffold_points, show_vertices)
        scaffold_geom.line_width = 1.0 
        scaffold_geom.color = [0.6,0.0,0.0,1.0] 
        scaffold_geom.selected_callback = self.select_coords
        scaffold_geom.select_vertex = True
        scaffold_geom.entity_indexes = range(0,len(scaffold_points))
        self.representations[VisHelixRepType.COORDINATES] = [scaffold_geom]
        self.graphics.add_render_geometry(scaffold_geom)

        # Create the staple geometry.
        name = "HelixStapleCoords:%s" % self.id
        staple_geom = VisGeometryPath(name, staple_points, show_vertices)
        staple_geom.color = [0.0,0.6,0.0,1.0] 
        staple_geom.line_width = 1.0 
        staple_geom.selected_callback = self.select_coords
        staple_geom.select_vertex = True
        staple_geom.entity_indexes = range(0,len(staple_points))
        self.graphics.add_render_geometry(staple_geom)
        self.representations[VisHelixRepType.COORDINATES].append(staple_geom) 

    def select_coords(self, geom, index):
        """ Process helix coordinates selection.

            Arguments:
                geom (VisGeometry): The geometry selected.
                index (int): The index into the geometry selected.
        """
        if "Scaffold" in geom.name:
            strand_type = "scaffold"
        else:
            strand_type = "staple"
        self._logger.info("Selected Helix %s coordinates. Base number %d" % (self.name, index+1))
        self._logger.info("Helix is %s " % (strand_type))
        self.print_info()

    def create_frames_rep(self):
        """ Create the geometry for the helix coordinates frames representation. """
        origins = self.vhelix.helix_axis_coords
        directions = self.vhelix.helix_axis_frames
        scale = 0.2
        name = "HelixFrame:%s" % self.id
        geom = VisGeometryAxes(name, origins, directions, scale)
        geom.selected_callback = self.select_frames
        self.representations[VisHelixRepType.COORDINATE_FRAMES] = [geom]
        self.graphics.add_render_geometry(geom)

    def select_frames(self, geom, index):
        """ Process helix node selection.

            Arguments:
                geom (VisGeometry): The geometry selected.
                index (int): The index into the geometry selected.
        """
        coords = self.vhelix.helix_axis_coords[index]
        self._logger.info("Selected Helix %s frame. Location in helix %d  Coordinates (%g %g %g) " % (self.name, index+1,
            coords[0], coords[1], coords[2]))
        self.print_info()

    def create_domains_rep(self):
        """ Create the geometry for the helix domains representation. """
        radius = 0.5
        self.representations[VisHelixRepType.DOMAINS] = []
        domain_list = self.dna_structure.domain_list
        domain_ids = self.vhelix.get_domain_ids()
        for id in domain_ids:
            domain = domain_list[id]
            point1,point2 = domain.get_end_points()
            point1 = point1.copy()
            point2 = point2.copy()
            if (domain.strand.is_scaffold):
                point1[2] += radius
                point2[2] += radius
            else:
                point1[2] -= radius
                point2[2] -= radius
            name = "HelixDomain:%s.%d" % (self.id, id)
            geom = VisGeometryCylinder(name, radius, point1, point2)
            geom.color = domain.color
            geom.selected_callback = self.select_domains
            self.representations[VisHelixRepType.DOMAINS].append(geom)
            self.graphics.add_render_geometry(geom)
        #__for domain in self.dna_structure.domain_list
    #__create_domains_rep(self):

    def select_domains(self, geom, index):
        """ Process helix geometry selection.

            Arguments:
                geom (VisGeometry): The geometry selected.
                index (int): The index into the geometry selected.
        """
        domain_id = int(geom.name.split(".")[1])
        domain_list = self.dna_structure.domain_list
        domain_ids = self.vhelix.get_domain_ids()
        domain = domain_list[domain_id]
        num_bases = len(domain.base_list)
        start_base = domain.base_list[0]
        end_base = domain.base_list[-1]
        strand_name = VisStrand.get_strand_name(domain.strand)
        self._logger.info("Selected Helix %s domain. " % (self.name))
        self._logger.info("Domain ID %d  Number of bases %d  Start pos %d  End pos %d" % (domain_id, num_bases,
            start_base.p, end_base.p))
        self._logger.info("Domain is part of strand %s" % (strand_name))
        self.print_info()

    def create_inserts_deletes_rep(self):
        """ Create the geometry for the helix inserts and deletes representation. 

            The inserts and deletes representation is visualized by displaying the staple and scaffold inserts and
            deletes as wireframe spheres.
        """
        # Create the inserts geometry.
        inserts = [i for i,base in enumerate(self.vhelix.staple_base_list) if base.num_insertions != 0]
        num_inserts = len(inserts)
        if num_inserts != 0:
            insert_origins = np.zeros((num_inserts,3), dtype=float)
            insert_directions = np.zeros((3,3,num_inserts), dtype=float)
            for i,j in enumerate(inserts): 
                base = self.vhelix.staple_base_list[j]
                insert_origins[i] = base.coordinates
                insert_directions[:,:,i] = base.ref_frame
            #__for id in base_ids
            show_vertices = True
            name = "HelixInserts:%s" % self.id
            scale = 0.2
            symbol = VisGeometrySymbols.BASE_INSERT
            inserts_geom = VisGeometrySymbols(name, symbol, insert_origins, insert_directions, scale)
            inserts_geom.line_width = 1.0 
            inserts_geom.color = [0.0,0.6,0.0,1.0] 
            inserts_geom.selected_callback = self.select_inserts
            inserts_geom.select_vertex = True
            inserts_geom.entity_indexes = range(0,len(inserts))
            self.representations[VisHelixRepType.INSERTS_DELETES] = [inserts_geom]
            self.graphics.add_render_geometry(inserts_geom)
        #__if num_inserts != 0

        # Create the deletes geometry.
        deletes = [i for i,base in enumerate(self.vhelix.staple_base_list) if base.num_deletions != 0]
        num_deletes = len(deletes)
        if num_deletes != 0:
            delete_origins = np.zeros((num_deletes,3), dtype=float)
            delete_directions = np.zeros((3,3,num_deletes), dtype=float)
            for i,j in enumerate(deletes): 
                base = self.vhelix.staple_base_list[j]
                delete_origins[i] = base.coordinates
                delete_directions[:,:,i] = base.ref_frame
            #__for id in base_ids
            show_vertices = True
            name = "HelixDeletes:%s" % self.id
            scale = 0.2
            symbol = VisGeometrySymbols.BASE_DELETE
            deletes_geom = VisGeometrySymbols(name, symbol, delete_origins, delete_directions, scale)
            deletes_geom.line_width = 1.0
            deletes_geom.color = [0.6,0.0,0.0,1.0]
            deletes_geom.selected_callback = self.select_deletes
            deletes_geom.select_vertex = True
            deletes_geom.entity_indexes = range(0,len(deletes))
            self.representations[VisHelixRepType.INSERTS_DELETES] = [deletes_geom]
            self.graphics.add_render_geometry(deletes_geom)
        #__if num_inserts != 0

        if (num_deletes == 0) and (num_inserts == 0):
            self.representations[VisHelixRepType.INSERTS_DELETES] = []

    def select_inserts(self, geom, index):
        """ Process helix inserts selection.

            Arguments:
                geom (VisGeometry): The geometry selected.
                index (int): The index into the geometry selected.
        """
        self._logger.info("Selected Helix %s insert." % (self.name)) 
        self.print_info()

    def select_deletes(self, geom, index):
        """ Process helix inserts selection.

            Arguments:
                geom (VisGeometry): The geometry selected.
                index (int): The index into the geometry selected.
        """
        self._logger.info("Selected Helix %s insert." % (self.name))
        self.print_info()

    def create_strands_rep(self):
        """ Create the geometry for the helix strands representation. """
        # Find the strands that pass through this helix.
        strand_list = []
        for strand in self.dna_structure.strands:
            if not strand.is_scaffold and (self.id in strand.helix_list):
                strand_list.append(strand)
        #__for strand in self.dna_structure
        # Create the strands geometry.
        show_verts = False
        show_arrows = True
        self.representations[VisHelixRepType.STRANDS] = []
        for strand in strand_list:
            base_coords = strand.get_base_coords()
            name = "HelixStrand:%s.%d" % (self.id, strand.id)
            geom = VisGeometryPath(name,base_coords,show_verts,show_arrows)
            geom.start_marker = True
            geom.line_width = 2.0
            geom.color = strand.color
            geom.data = strand
            geom.selected_callback = self.select_strand
            geom.select_vertex = True
            geom.entity_indexes = range(0,len(base_coords))
            self.representations[VisHelixRepType.STRANDS].append(geom)
            self.graphics.add_render_geometry(geom)
        #__for strand in strand_list
    #__create_strands_rep

    def select_strand(self, geom, index):
        """ Process helix strand selection.

            Arguments:
                geom (VisGeometry): The geometry selected.
                index (int): The index into the geometry selected.
        """
        strand = geom.data
        strand_name = VisStrand.get_strand_name(strand)
        base_id = strand.tour[index]
        base = self.dna_structure.base_connectivity[base_id-1]
        self._logger.info("Selected Helix %s Strand %s" % (self.name, strand_name))
        self._logger.info("Location in strand path %d  Vhelix %d  Position %d  " % (index+1, base.h, base.p))
        self.print_info()
