from scipy import misc
from polaris import util
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import vtk
import os
from dipy.viz import window, actor
from dipy.viz.colormap import colormap_lookup_table, create_colormap
from dipy.utils.optpkg import optional_package
numpy_support, have_ns, _ = optional_package('vtk.util.numpy_support')

def plot_parallels(raw_data, out_path='out/', outer_box=True, axes=True,
                   clip_neg=False, size=(600,600), mask=None, scale=1,
                   azimuth=0, elevation=0, zoom=1.7):
    # Prepare output
    if not os.path.exists(out_path):
        os.makedirs(out_path)

    # Mask
    if mask is None:
        mask = np.ones(raw_data.shape)
    raw_data = raw_data*mask
        
    # Render
    ren = window.Renderer()
    ren.background([1,1,1])

    # Add visuals to renderer
    data = np.zeros(raw_data.shape)

    # X MIP
    data[data.shape[0]//2,:,:] = np.max(raw_data, axis=0)
    slice_actorx = actor.slicer(data, value_range=(0,1), interpolation='nearest')
    slice_actorx.display(slice_actorx.shape[0]//2, None, None)
    ren.add(slice_actorx)

    # Y MIP
    data[:,data.shape[1]//2,:] = np.max(raw_data, axis=1)
    slice_actory = actor.slicer(data, value_range=(0,1), interpolation='nearest')
    slice_actory.display(None, slice_actory.shape[1]//2, None)
    ren.add(slice_actory)

    # Z MIP
    data[:,:,data.shape[2]//2] = np.max(raw_data, axis=-1)
    slice_actorz = actor.slicer(data, value_range=(0,1), interpolation='nearest')
    slice_actorz.display(None, None, slice_actorz.shape[2]//2)
    ren.add(slice_actorz)

    X = raw_data.shape[0] - 1
    Y = raw_data.shape[1] - 1
    Z = raw_data.shape[2] - 1

    if outer_box:
        c = np.array([0,0,0])
        ren.add(actor.line([np.array([[0,0,0],[X,0,0],[X,Y,0],[0,Y,0],
                                      [0,0,0],[0,Y,0],[0,Y,Z],[0,0,Z],
                                      [0,0,0],[X,0,0],[X,0,Z],[0,0,Z]])], colors=c))
        ren.add(actor.line([np.array([[X,0,Z],[X,Y,Z],[X,Y,0],[X,Y,Z],
                                      [0,Y,Z]])], colors=c))
    NN = np.max([X, Y, Z])
    # Add invisible actors to set FOV
    ren.add(actor.line([np.array([[0,0,0],[NN,0,0]])], colors=np.array([1,1,1]), linewidth=1))
    ren.add(actor.line([np.array([[0,0,0],[0,NN,0]])], colors=np.array([1,1,1]), linewidth=1))
    ren.add(actor.line([np.array([[0,0,0],[0,0,NN]])], colors=np.array([1,1,1]), linewidth=1))
    # Add colored axes
    if axes:
        ren.add(actor.line([np.array([[0,0,0],[NN/10,0,0]])], colors=np.array([1,0,0]), linewidth=4))
        ren.add(actor.line([np.array([[0,0,0],[0,NN/10,0]])], colors=np.array([0,1,0]), linewidth=4))
        ren.add(actor.line([np.array([[0,0,0],[0,0,NN/10]])], colors=np.array([0,0,1]), linewidth=4))

    # Setup vtk renderers
    renWin = vtk.vtkRenderWindow()
    renWin.AddRenderer(ren)
    renWin.SetSize(size[0], size[1])
    iren = vtk.vtkRenderWindowInteractor()
    iren.SetRenderWindow(renWin)
    ren.ResetCamera()
    ren.azimuth(azimuth)
    ren.elevation(elevation)

    writer = vtk.vtkPNGWriter()
    az = 0

    filenames = ['yz', 'xy', 'xz']
    zooms = [zoom, 1.0, 1.0]
    azs = [90, -90, 0]
    els = [0, 0, 90]
    for i in range(3):
        ren.projection(proj_type='parallel')
        ren.zoom(zooms[i])
        ren.azimuth(azs[i])
        ren.elevation(els[i])
        ren.reset_clipping_range()
        renderLarge = vtk.vtkRenderLargeImage()
        renderLarge.SetMagnification(1)
        renderLarge.SetInput(ren)
        renderLarge.Update()
        writer.SetInputConnection(renderLarge.GetOutputPort())
        writer.SetFileName(out_path + filenames[i] + '.png')
        writer.Write()
        
def plot5d(filename, data, row_labels=None, col_labels=None, yscale_label=None,
           force_bwr=False, normalize=False):

    if np.min(data) < 0 or force_bwr:
        colormap = 'bwr'
        vmin = -1
        vmax = 1
    else:
        colormap = 'gray'
        vmin = 0
        vmax = 1

    if normalize:
        data = data/np.max(data)
    
    inches = 2
    rows = data.shape[-1]
    cols = data.shape[-2] + 1
    widths = [1]*(cols - 1) + [0.05]
    heights = [1]*rows
    M = np.max(data.shape)
    x_frac = data.shape[0]/M
    f = plt.figure(figsize=(inches*np.sum(widths), inches*np.sum(heights)))
    spec = gridspec.GridSpec(ncols=cols, nrows=rows, width_ratios=widths,
                             height_ratios=heights, hspace=0.25, wspace=0.15)
    for row in range(rows):
        for col in range(cols):
            if col != cols - 1:
                data3 = data[:,:,:,col,row]
                plot_parallels(data3, out_path='parallels/', outer_box=False,
                                   axes=False, clip_neg=False, azimuth=0,
                                   elevation=0)
                plot_images(['parallels/yz.png', 'parallels/xy.png', 'parallels/xz.png'],
                                f, spec, row, col,
                                col_labels=col_labels, row_labels=row_labels,
                                vmin=vmin, vmax=vmax, colormap=colormap,
                                rows=rows, cols=cols, x_frac=x_frac, yscale_label=yscale_label)
            elif col == cols - 1 and row == rows - 1:
                plot_colorbar(f, spec, row, col, vmin, vmax, colormap)

    f.savefig(filename, bbox_inches='tight')
    
def plot_images(images, f, spec, row, col, col_labels, row_labels, vmin, vmax,
                colormap, rows, cols, x_frac, yscale_label, pos=(-0.05, 1.05, 0.5, 0.5)):
    mini_spec = gridspec.GridSpecFromSubplotSpec(2, 2, subplot_spec=spec[row, col], hspace=0.1, wspace=0.1)
    for a in range(2):
        for b in range(2):
            ax = f.add_subplot(mini_spec[a, b])
            if a == 0 and b == 0:
                image = images[0]
            if a == 0 and b == 1:
                image = images[1]
            if a == 1 and b == 1:
                image = images[2]
                draw_annotations(ax, row, col, row_labels, col_labels, pos=pos)
            if a == 1 and b == 0:
                image = None
            if image is not None:
                im = misc.imread(image)
                ax.imshow(im, interpolation='none', origin='upper', extent=[-24, 24, -24, 24], aspect=1)
            ax.axis('off')
            if col == (cols - 2) and row == rows - 1 and a == 1 and b == 1 and yscale_label is not None:
                ax.annotate(yscale_label, xy=(x_frac/2,-0.3), xytext=(x_frac/2, -0.3), xycoords='axes fraction', textcoords='axes fraction', va='center', ha='center', fontsize=10)
                ax.annotate('', xy=(0, -0.1), xytext=(x_frac, -0.1), xycoords='axes fraction', textcoords='axes fraction', va='center', arrowprops=dict(arrowstyle='|-|, widthA=0.2, widthB=0.2', shrinkA=0.05, shrinkB=0.05, lw=0.5))
                
def plot_colorbar(f, spec, row, col, vmin, vmax, colormap):
    ax = f.add_subplot(spec[row, col])
    X, Y = np.meshgrid(np.linspace(vmin, vmax, 100),
                       np.linspace(vmin, vmax, 100))
    ax.imshow(Y, cmap=colormap, vmin=vmin, vmax=vmax, interpolation='none',
              extent=[vmin,vmax,vmin,vmax], origin='lower', aspect='auto')
    ax.set_xlim([vmin,vmax])
    ax.set_ylim([vmin,vmax])
    ax.tick_params(direction='out', left=False, right=True)
    ax.xaxis.set_ticks([])
    ax.yaxis.tick_right()
    if vmin == -1:
        ax.yaxis.set_ticks([-1.0, 0, 1.0])
    else:
        ax.yaxis.set_ticks([0, 0.5, 1.0])

def draw_annotations(ax, row, col, row_labels, col_labels, pos=(-0.05, 1.05, 0.5, 0.5)):
    xc = pos[0]
    yc = pos[1]
    d1 = pos[2]
    d2 = pos[3]
    ax.annotate('', xy=(xc,yc), xytext=(xc+d1, yc), xycoords='axes fraction', textcoords='axes fraction', va='center', arrowprops=dict(arrowstyle="<-", shrinkB=0, lw=0.5))
    ax.annotate('', xy=(xc,yc), xytext=(xc-d1, yc), xycoords='axes fraction', textcoords='axes fraction', ha='center', arrowprops=dict(arrowstyle="<-", shrinkB=0, lw=0.5))
    ax.annotate('', xy=(xc,yc), xytext=(xc, yc+d1), xycoords='axes fraction', textcoords='axes fraction', ha='center', arrowprops=dict(arrowstyle="<-", shrinkB=0, lw=0.5))
    ax.annotate('', xy=(xc,yc), xytext=(xc, yc-d1), xycoords='axes fraction', textcoords='axes fraction', va='center', arrowprops=dict(arrowstyle="<-", shrinkB=0, lw=0.5))
    ax.annotate('$x$', xy=(xc,yc), xytext=(xc+d2, yc), xycoords='axes fraction', textcoords='axes fraction', va='center', ha='center', fontsize=6)
    ax.annotate('$z$', xy=(xc,yc), xytext=(xc-d2, yc), xycoords='axes fraction', textcoords='axes fraction', va='center', ha='center', fontsize=6)
    ax.annotate('$y$', xy=(xc,yc), xytext=(xc, yc+d2), xycoords='axes fraction', textcoords='axes fraction', va='center', ha='center', fontsize=6)
    ax.annotate('$z$', xy=(xc,yc), xytext=(xc, yc-d2), xycoords='axes fraction', textcoords='axes fraction', va='center', ha='center', fontsize=6)
    if col_labels is not None:
        ax.annotate(col_labels[row,col], xy=(xc,yc), xytext=(0, 2.3), xycoords='axes fraction', textcoords='axes fraction', va='center', ha='center', fontsize=10)
    if col == 0 and row_labels is not None:
        ax.annotate(row_labels[row], xy=(xc,yc), xytext=(-1.55, 1), xycoords='axes fraction', textcoords='axes fraction', va='center', ha='center', fontsize=10, rotation=90)

def odf_sparse(odfsh, Binv, globalpeak, affine=None, mask=None, sphere=None, scale=2.2,
               norm=True, radial_scale=True, opacity=1.,
               colormap='plasma', global_cm=False):
    if mask is None:
        mask = np.ones(odfsh.shape[:3], dtype=np.bool)
    else:
        mask = mask.astype(np.bool)

    szx, szy, szz = odfsh.shape[:3]

    class OdfSlicerActor(vtk.vtkLODActor):

        def display_extent(self, x1, x2, y1, y2, z1, z2):
            tmp_mask = np.zeros(odfsh.shape[:3], dtype=np.bool)
            tmp_mask[x1:x2 + 1, y1:y2 + 1, z1:z2 + 1] = True
            tmp_mask = np.bitwise_and(tmp_mask, mask)

            self.mapper = _odf_slicer_mapper(odfsh=odfsh, Binv=Binv,
                                             globalpeak=globalpeak,
                                             affine=affine,
                                             mask=tmp_mask,
                                             sphere=sphere,
                                             scale=scale,
                                             norm=norm,
                                             radial_scale=radial_scale,
                                             opacity=opacity,
                                             colormap=colormap,
                                             global_cm=global_cm)
            self.SetMapper(self.mapper)

        def display(self, x=None, y=None, z=None):
            if x is None and y is None and z is None:
                self.display_extent(0, szx - 1, 0, szy - 1, 0, szz - 1)

            if x is not None:
                self.display_extent(x, x, 0, szy - 1, 0, szz - 1)
            if y is not None:
                self.display_extent(0, szx - 1, y, y, 0, szz - 1)
            if z is not None:
                self.display_extent(0, szx - 1, 0, szy - 1, z, z)

    odf_actor = OdfSlicerActor()
    odf_actor.display_extent(0, szx - 1, 0, szy - 1, 0, szz - 1)

    return odf_actor

def _odf_slicer_mapper(odfsh, Binv, globalpeak, affine=None, mask=None,
                       sphere=None, scale=2.2,
                       norm=True, radial_scale=True, opacity=1.,
                       colormap='plasma', global_cm=False):
    if mask is None:
        mask = np.ones(odfs.shape[:3])

    ijk = np.ascontiguousarray(np.array(np.nonzero(mask)).T)

    if len(ijk) == 0:
        return None

    if affine is not None:
        ijk = np.ascontiguousarray(apply_affine(affine, ijk))

    faces = np.asarray(sphere.faces, dtype=int)
    vertices = sphere.vertices

    all_xyz = []
    all_faces = []
    all_ms = []
    for (k, center) in enumerate(ijk):
        msh = odfsh[tuple(center.astype(np.int))].copy()
        m = np.matmul(Binv.T, msh)
        if k == 0:
            m[0] = -1*globalpeak

        if norm:
            m /= np.abs(m).max()

        if radial_scale:
            xyz = vertices * m[:, None]
        else:
            xyz = vertices.copy()

        all_xyz.append(scale * xyz + center)
        all_faces.append(faces + k * xyz.shape[0])
        all_ms.append(m)

    all_xyz = np.ascontiguousarray(np.concatenate(all_xyz))
    all_xyz_vtk = numpy_support.numpy_to_vtk(all_xyz, deep=True)

    all_faces = np.concatenate(all_faces)
    all_faces = np.hstack((3 * np.ones((len(all_faces), 1)),
                           all_faces))
    ncells = len(all_faces)

    all_faces = np.ascontiguousarray(all_faces.ravel(), dtype='i8')
    all_faces_vtk = numpy_support.numpy_to_vtkIdTypeArray(all_faces,
                                                          deep=True)

    if global_cm:
        all_ms = np.ascontiguousarray(
            np.concatenate(all_ms), dtype='f4')

    points = vtk.vtkPoints()
    points.SetData(all_xyz_vtk)

    cells = vtk.vtkCellArray()
    cells.SetCells(ncells, all_faces_vtk)

    if colormap is not None:
        if global_cm:
            cols = create_colormap(all_ms.ravel(), colormap)
        else:
            cols = np.zeros((ijk.shape[0],) + sphere.vertices.shape,
                            dtype='f4')
            for k in range(ijk.shape[0]):
                tmp = create_colormap(all_ms[k].ravel(), colormap)
                cols[k] = tmp.copy()

            cols = np.ascontiguousarray(
                np.reshape(cols, (cols.shape[0] * cols.shape[1],
                           cols.shape[2])), dtype='f4')

        vtk_colors = numpy_support.numpy_to_vtk(
            np.asarray(255 * cols),
            deep=True,
            array_type=vtk.VTK_UNSIGNED_CHAR)

        vtk_colors.SetName("Colors")

    polydata = vtk.vtkPolyData()
    polydata.SetPoints(points)
    polydata.SetPolys(cells)

    if colormap is not None:
        polydata.GetPointData().SetScalars(vtk_colors)

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(polydata)

    return mapper

def peak_slicer(peaks_dirs, peaks_values=None, mask=None, affine=None,
                colors=(1, 0, 0), opacity=1., linewidth=1,
                lod=False, lod_points=10 ** 4, lod_points_size=3):
    peaks_dirs = np.asarray(peaks_dirs)
    if peaks_dirs.ndim > 5:
        raise ValueError("Wrong shape")

    peaks_dirs = actor._makeNd(peaks_dirs, 5)
    if peaks_values is not None:
        peaks_values = actor._makeNd(peaks_values, 4)

    grid_shape = np.array(peaks_dirs.shape[:3])

    if mask is None:
        mask = np.ones(grid_shape).astype(np.bool)

    class PeakSlicerActor(vtk.vtkLODActor):

        def display_extent(self, x1, x2, y1, y2, z1, z2):
            tmp_mask = np.zeros(grid_shape, dtype=np.bool)
            tmp_mask[x1:x2 + 1, y1:y2 + 1, z1:z2 + 1] = True
            tmp_mask = np.bitwise_and(tmp_mask, mask)

            ijk = np.ascontiguousarray(np.array(np.nonzero(tmp_mask)).T)
            if len(ijk) == 0:
                self.SetMapper(None)
                return
            if affine is not None:
                ijk_trans = np.ascontiguousarray(apply_affine(affine, ijk))
            list_dirs = []
            for index, center in enumerate(ijk):
                # center = tuple(center)
                if affine is None:
                    xyz = center[:, None]
                else:
                    xyz = ijk_trans[index][:, None]
                xyz = xyz.T
                for i in range(peaks_dirs[tuple(center)].shape[-2]):

                    if peaks_values is not None:
                        pv = peaks_values[tuple(center)][i]
                    else:
                        pv = 1.
                    symm = np.vstack((-peaks_dirs[tuple(center)][i] * pv + xyz,
                                      peaks_dirs[tuple(center)][i] * pv + xyz))
                    list_dirs.append(symm)

            self.mapper = actor.line(list_dirs, colors=colors,
                                     opacity=opacity, linewidth=linewidth,
                                     lod=lod, lod_points=lod_points,
                                     lod_points_size=lod_points_size).GetMapper()
            self.SetMapper(self.mapper)

        def display(self, x=None, y=None, z=None):
            if x is None and y is None and z is None:
                self.display_extent(0, szx - 1, 0, szy - 1, 0, szz - 1)
            if x is not None:
                self.display_extent(x, x, 0, szy - 1, 0, szz - 1)
            if y is not None:
                self.display_extent(0, szx - 1, y, y, 0, szz - 1)
            if z is not None:
                self.display_extent(0, szx - 1, 0, szy - 1, z, z)

    peak_actor = PeakSlicerActor()

    szx, szy, szz = grid_shape
    peak_actor.display_extent(0, szx - 1, 0, szy - 1, 0, szz - 1)

    return peak_actor
