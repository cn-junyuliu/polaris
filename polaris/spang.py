import subprocess
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib import rc
#rc('text', usetex=True)
from polaris import viz, util
import numpy as np
from dipy.viz import window, actor, fvtk
from dipy.data import get_sphere
import vtk
from tqdm import tqdm
import tifffile
import os
import logging
log = logging.getLogger('log')

class Spang:
    """
    A Spang (short for spatio-angular density) is a representation of a 
    spatio-angular density f(r, s) stored as a 4D array of voxel values 
    and spherical harmonic coefficients [x, y, z, j]. A Spang object is 
    a discretized member of object space U. 
    """
    def __init__(self, f=np.zeros((3,3,3,1)), vox_dim=(1,1,1),
                 sphere=get_sphere('symmetric724')):
        self.X = f.shape[0]
        self.Y = f.shape[1]
        self.Z = f.shape[2]
        
        # Calculate band dimensions
        self.lmax, mm = util.j2lm(f.shape[-1] - 1)
        self.J = util.maxl2maxj(self.lmax)

        # Fill the rest of the last l band with zeros
        if f.shape[-1] != self.J:
            temp = np.zeros((self.X, self.Y, self.Z, self.J))
            temp[...,:f.shape[-1]] = f
            self.f = temp
        else:
            self.f = f

        self.vox_dim = vox_dim
        self.sphere = sphere
        self.N = len(self.sphere.theta)
        self.calc_B()
        
    def calc_B(self):
        # Calculate odf to sh matrix
        B = np.zeros((self.N, self.J))
        for (n, j), x in np.ndenumerate(B):
            l, m = util.j2lm(j)
            B[n, j] = util.spZnm(l, m, self.sphere.theta[n], self.sphere.phi[n])
        self.B = B
        self.Binv = np.linalg.pinv(self.B, rcond=1e-15)

    def density(self, normalized=True):
        if normalized:
            return self.f[...,0]/np.max(self.f[...,0])
        else:
            return self.f[...,0]
        
    def gfa(self):
        return np.nan_to_num(np.sqrt(1 - (self.f[...,0]**2)/np.sum(self.f**2, axis=-1)))

    def tensor(self):
        log.info("Calculating tensor fits")
        M = np.load(os.path.join(os.path.dirname(__file__), 'harmonics/sh2tensor.npy'))
        Di = np.einsum('ijkl,lm->ijkm', self.f[...,0:6], M)
        D = np.zeros(self.f.shape[0:3]+(3,3), dtype=np.float32)
        D[...,0,0] = Di[...,0]; D[...,0,1] = Di[...,3]; D[...,0,2] = Di[...,5];
        D[...,1,0] = Di[...,3]; D[...,1,1] = Di[...,1]; D[...,1,2] = Di[...,4];
        D[...,2,0] = Di[...,5]; D[...,2,1] = Di[...,4]; D[...,2,2] = Di[...,2];
        eigs = np.linalg.eigh(D)
        principal = eigs[1][...,-1]*eigs[1][...,-1]
        return Di.astype(np.float32), principal.astype(np.float32)
        
    def save_summary(self, filename='out.pdf', density_filter=None, mag=4,
                     mask=None, scale=1, keep_parallels=False, skip_n=1):
        log.info('Generating ' + filename)
        if density_filter is not None:
            density_mask = self.density() > density_filter
            mask = np.logical_or(mask, density_mask).astype(np.bool)
        pos = (-0.05, 1.05, 0.5, 0.55) # Arrow and label positions
        vmin = 0
        vmax = 1
        inches = 4
        rows = 2
        cols = 3
        colormap = 'Reds'
        widths = [1]*cols
        heights = [1]*rows
        M = np.max(self.f.shape)
        x_frac = self.f.shape[0]/M
        if density_filter is None:
            filter_label = ''
        else:
            filter_label = '\n where density $>$ ' + str(density_filter)
        if skip_n == 1:
            skip_label = ''
        else:
            skip_label = '\n downsampled ' + str(skip_n) + '$\\times$'
        col_labels = np.array([['ODF', 'Density', 'GFA'], ['Peak', 'Ellipsoid', 'Principal']])
        f = plt.figure(figsize=(inches*np.sum(widths), inches*np.sum(heights)))
        spec = gridspec.GridSpec(ncols=cols, nrows=rows, width_ratios=widths,
                                 height_ratios=heights, hspace=0.1, wspace=0.075)
        for row in range(rows):
            for col in range(cols):
                if col < 3:
                    yscale_label = None
                    if row == 0 and col == 0:
                        bar = True
                        bar_label = 'ODF radius' + skip_label + filter_label
                        colormap = 'Reds'
                        self.visualize(out_path='parallels/', zoom_start=1.7,
                                       outer_box=False, axes=False,
                                       clip_neg=False, azimuth=0, elevation=0,
                                       n_frames=1, mag=mag, video=False, scale=scale,
                                       interact=False, viz_type='ODF',
                                       save_parallels=True, mask=mask, skip_n=skip_n)
                    if row == 1 and col == 1:
                        bar = False
                        bar_label = 'Principal' + skip_label + filter_label
                        self.visualize(out_path='parallels/', zoom_start=1.7,
                                       outer_box=False, axes=False,
                                       clip_neg=False, azimuth=0, elevation=0,
                                       n_frames=1, mag=mag, video=False, scale=scale,
                                       interact=False, viz_type='Ellipsoid',
                                       save_parallels=True, mask=mask, skip_n=skip_n)
                    if row == 1 and col == 2:
                        bar = False
                        bar_label = 'Principal' + skip_label + filter_label
                        self.yscale = 1e-3*self.vox_dim[1]*self.f.shape[0]
                        yscale_label = '{:.2f}'.format(self.yscale) + ' $\mu$m'
                        self.visualize(out_path='parallels/', zoom_start=1.7,
                                       outer_box=False, axes=False,
                                       clip_neg=False, azimuth=0, elevation=0,
                                       n_frames=1, mag=mag, video=False, scale=scale,
                                       interact=False, viz_type='Principal',
                                       save_parallels=True, mask=mask, skip_n=skip_n)
                    if row == 1 and col == 0:
                        bar = False
                        bar_label = 'Peak' + skip_label + filter_label
                        self.visualize(out_path='parallels/', zoom_start=1.7,
                                       outer_box=False, axes=False,
                                       clip_neg=False, azimuth=0, elevation=0,
                                       n_frames=1, mag=mag, video=False, scale=scale,
                                       interact=False, viz_type='Peak',
                                       save_parallels=True, mask=mask, skip_n=skip_n)
                    if row == 0 and col == 1:
                        colormap = 'gray'
                        bar = True
                        bar_label = 'Density'
                        viz.plot_parallels(self.density(), out_path='parallels/', outer_box=False,
                                           axes=False, clip_neg=False, azimuth=0,
                                           elevation=0, scale=scale)
                    if row == 0 and col == 2:
                        colormap = 'gray'
                        bar = True
                        bar_label = 'GFA' + filter_label
                        viz.plot_parallels(self.gfa(), out_path='parallels/', outer_box=False,
                                           axes=False, clip_neg=False, azimuth=0,
                                           elevation=0, scale=scale, mask=mask)

                    viz.plot_images(['parallels/yz.png', 'parallels/xy.png', 'parallels/xz.png'],
                                    f, spec, row, col,
                                    col_labels=col_labels, row_labels=None,
                                    vmin=vmin, vmax=vmax, colormap=colormap,
                                    rows=rows, cols=cols, x_frac=x_frac,
                                    yscale_label=yscale_label, pos=pos, bar=bar, bar_label=bar_label)
                    #if not keep_parallels:
                        #subprocess.call(['rm', '-r', 'parallels'])
                    
                elif col == 3:
                    viz.plot_colorbar(f, spec, row, col, vmin, vmax, colormap)

        log.info('Saving ' + filename)
        f.savefig(filename, bbox_inches='tight')

    def save_mips(self, filename='spang_mips.pdf'):
        log.info('Writing '+filename)
        col_labels = np.apply_along_axis(util.j2str, 1, np.arange(self.J)[:,None])[None,:]
        viz.plot5d(filename, self.f[...,None], col_labels=col_labels)
            
    def save_tiff(self, filename='sh.tif', data=None):
        if data is None:
            data = self.f
        
        log.info('Writing '+filename)
        with tifffile.TiffWriter(filename, imagej=True) as tif:
            if data.ndim == 4:
                d = np.moveaxis(data, [2, 3, 1, 0], [0, 1, 2, 3])
                tif.save(d[None,:,:,:,:]) # TZCYXS
            elif data.ndim == 3:
                d = np.moveaxis(data, [2, 1, 0], [0, 1, 2])
                tif.save(d[None,:,None,:,:].astype(np.float32)) # TZCYXS
                
    def read_tiff(self, filename):
        log.info('Reading '+filename)
        with tifffile.TiffFile(filename) as tf:
            self.f = np.moveaxis(tf.asarray(), [0, 1, 2, 3], [2, 3, 1, 0])
        self.X = self.f.shape[0]
        self.Y = self.f.shape[1]
        self.Z = self.f.shape[2]

    def save_stats(self, folder='./', save_sh=False):
        if not os.path.exists(folder):
            os.makedirs(folder)
        if save_sh:
            self.save_tiff(filename=folder+'sh.tif', data=self.f)
        self.save_tiff(filename=folder+'density.tif', data=self.density())
        self.save_tiff(filename=folder+'gfa.tif', data=self.gfa())
        
    def visualize(self, out_path='out/', outer_box=True, axes=True,
                  clip_neg=False, azimuth=0, elevation=0, n_frames=1,
                  size=(600,600), mag=4, video=False, viz_type='ODF', mask=None,
                  skip_n=1, scale=1, zoom_start=None, zoom_end=None,
                  interact=False, save_parallels=False, gfa_filter=0,
                  my_cam=None, compress=True, roi=None):
        log.info('Preparing to render ' + out_path)
        
        # Prepare output
        if not os.path.exists(out_path):
           os.makedirs(out_path)
            
        # Mask
        if mask is None:
            mask = np.ones((self.X, self.Y, self.Z), dtype=np.bool)
        skip_mask = np.zeros(mask.shape, dtype=np.bool)
        skip_mask[::skip_n,::skip_n,::skip_n] = 1
        global_mask = np.logical_and(mask, skip_mask)

        
        # Setup vtk renderers
        renWin = vtk.vtkRenderWindow()
        if not interact:
            renWin.SetOffScreenRendering(1)
        if isinstance(viz_type, str):
            viz_type = [viz_type]

        # Rows and columns
        cols = len(viz_type)
        if roi is None:
            rows = 1
        else:
            rows = 2
            
        renWin.SetSize(500*mag*cols, 500*mag*rows)

        # Select background color
        if save_parallels:
            bg_color = [1,1,1]
            line_color = np.array([0,0,0])
            line_bcolor = np.array([1,1,1])
        else:
            bg_color = [0,0,0]
            line_color = np.array([1,1,1])
            line_bcolor = np.array([0,0,0])

        # For each viz_type
        rens = []
        for row in range(rows):
            for col in range(cols):
                # Render
                ren = window.Renderer()
                rens.append(ren)
                ren.background(bg_color)
                ren.SetViewport(col/cols,(rows - row - 1)/rows,(col+1)/cols,(rows - row)/rows)
                renWin.AddRenderer(ren)
                iren = vtk.vtkRenderWindowInteractor()
                iren.SetRenderWindow(renWin)

                if row == 0:
                    data = self.f
                    my_mask = global_mask
                    scale = scale
                else:
                    data = self.f[roi[0][0]:roi[1][0], roi[0][1]:roi[1][1], roi[0][2]:roi[1][2], :]
                    my_mask = mask[roi[0][0]:roi[1][0], roi[0][1]:roi[1][1], roi[0][2]:roi[1][2]]
                    scale = 1.0

                # Add visuals to renderer
                if viz_type[col] == "ODF":
                    log.info('Rendering '+str(np.sum(mask) - 8) + ' ODFs')
                    fodf_spheres = viz.odf_sparse(data, self.Binv, sphere=self.sphere,
                                                  scale=skip_n*scale*0.5, norm=False,
                                                  colormap='bwr', mask=my_mask,
                                                  global_cm=True)

                    ren.add(fodf_spheres)
                elif viz_type[col] == "Ellipsoid":
                    log.info('Rendering '+str(np.sum(mask) - 8) + ' ellipsoids')
                    fodf_peaks = viz.tensor_slicer_sparse(data,
                                                          sphere=self.sphere,
                                                          scale=skip_n*scale*0.5,
                                                          mask=my_mask)
                    ren.add(fodf_peaks)
                elif viz_type[col] == "Peak":
                    log.info('Rendering '+str(np.sum(mask) - 8) + ' peaks')
                    fodf_peaks = viz.peak_slicer_sparse(data, self.Binv, self.sphere.vertices, 
                                                        scale=skip_n*scale*0.5,
                                                        mask=my_mask)
                    ren.add(fodf_peaks)
                elif viz_type[col] == "Principal":
                    log.info('Rendering '+str(np.sum(mask) - 8) + ' principals')
                    fodf_peaks = viz.principal_slicer_sparse(data, self.Binv, self.sphere.vertices,
                                                             scale=skip_n*scale*0.5,
                                                             mask=my_mask)
                    ren.add(fodf_peaks)
                elif viz_type[col] == "Density":
                    log.info('Rendering density')
                    volume = viz.density_slicer(data[...,0])
                    ren.add(volume)

                X = np.float(data.shape[0])
                Y = np.float(data.shape[1])
                Z = np.float(data.shape[2])

                # Titles
                textProperty = vtk.vtkTextProperty()
                textProperty.SetFontSize(25*mag)
                textProperty.SetFontFamilyToArial()
                textProperty.BoldOn()
                textProperty.SetJustificationToCentered()
                
                if row == 0:
                    textmapper = vtk.vtkTextMapper()
                    textmapper.SetTextProperty(textProperty)
                    textmapper.SetInput(viz_type[col])

                    textactor = vtk.vtkActor2D()
                    textactor.SetMapper(textmapper)
                    textactor.SetPosition(250*mag, 500*mag - 25*(mag+1))

                    ren.AddActor(textactor)
                    
                # Scale bar
                if col == cols - 1 and not save_parallels:
                    textmapper = vtk.vtkTextMapper()
                    textmapper.SetTextProperty(textProperty)
                    yscale = 1e-3*self.vox_dim[1]*data.shape[1]
                    yscale_label = '{:.2f}'.format(yscale) + ' um'
                    textmapper.SetInput(yscale_label)

                    textactor = vtk.vtkActor2D()
                    textactor.SetMapper(textmapper)
                    textactor.SetPosition(250*mag, 5*(mag+1))
                    ren.AddActor(textactor)

                    viz.draw_scale_bar(ren, X, Y, Z, line_color)

                # Draw boxes
                Nmax = np.max([X, Y, Z])
                if outer_box:
                    if row == 0:
                        viz.draw_outer_box(ren, [[0,0,0],[X,Y,Z]], line_color)
                    if row == 1:
                        viz.draw_outer_box(ren, [[0,0,0],[X,Y,Z]], [0,1,1])
                else:
                    ren.add(actor.line([np.array([[0,0,0],[Nmax,0,0]])], colors=line_bcolor, linewidth=1))
                    ren.add(actor.line([np.array([[0,0,0],[0,Nmax,0]])], colors=line_bcolor, linewidth=1))
                    ren.add(actor.line([np.array([[0,0,0],[0,0,Nmax]])], colors=line_bcolor, linewidth=1))

                # Add colored axes
                if axes:
                    viz.draw_axes(ren, [[0,0,0], [X,Y,Z]])

                # Draw roi box
                if row == 0 and roi is not None:
                    maxROI = np.max([roi[1][0] - roi[0][0], roi[1][1] - roi[0][1], roi[1][2] - roi[0][2]])
                    maxXYZ = np.max([self.X, self.Y, self.Z])
                    viz.draw_outer_box(ren, roi, [0,1,1], lw=0.3*maxXYZ/maxROI)
                    viz.draw_axes(ren, roi, lw=0.3*maxXYZ/maxROI)

                # Setup cameras
                Rmax = np.linalg.norm([Z/2, X/2, Y/2])
                Rcam_rad = Rmax/np.tan(np.pi/12)        
                Ntmax = np.max([X, Y])
                ZZ = Z
                if ZZ > Ntmax:
                    Rcam_edge = np.max([X/2, Y/2])
                else:
                    Rcam_edge = np.min([X/2, Y/2])
                Rcam = Rcam_edge + Rcam_rad
                if my_cam is None:
                    cam = ren.GetActiveCamera()
                    cam.SetPosition((X//2 + Rcam, Y//2, Z//2))
                    cam.SetViewUp((0, 0, 1))
                    cam.SetFocalPoint((X//2, Y//2, Z//2))
                else:
                    ren.set_camera(*my_cam)
                ren.azimuth(azimuth)
                ren.elevation(elevation)

        # Setup writer
        writer = vtk.vtkTIFFWriter()
        if not compress:
            writer.SetCompressionToNoCompression()

        # Set zooming
        if zoom_start is None:
            if save_parallels:
                zoom_start = 1.7
                zoom_end = 1.7
            else:
                zoom_start = 1.3
                zoom_end = 1.3

        # Execute renders
        az = 0
        naz = np.ceil(360/n_frames)
        log.info('Rendering ' + out_path)
        if save_parallels:
            # Parallel rendering for summaries
            filenames = ['yz', 'xy', 'xz']
            zooms = [zoom_start, 1.0, 1.0]
            azs = [90, -90, 0]
            els = [0, 0, 90]
            ren.projection(proj_type='parallel')
            ren.reset_camera()
            for i in tqdm(range(3)):
                ren.zoom(zooms[i])
                ren.azimuth(azs[i])
                ren.elevation(els[i])
                ren.reset_clipping_range()
                renderLarge = vtk.vtkRenderLargeImage()
                renderLarge.SetMagnification(1)
                renderLarge.SetInput(ren)
                renderLarge.Update()
                writer.SetInputConnection(renderLarge.GetOutputPort())
                writer.SetFileName(out_path + filenames[i] + '.tif')
                writer.Write()
        else:
            # Rendering for movies 
            for ren in rens:
                ren.zoom(zoom_start)
            for i in tqdm(range(n_frames)):
                for ren in rens:
                    ren.zoom(1 + ((zoom_end - zoom_start)/n_frames))
                    ren.azimuth(az)
                renderLarge = vtk.vtkRenderLargeImage()
                renderLarge.SetMagnification(1)
                renderLarge.SetInput(ren)
                renderLarge.Update()
                writer.SetInputConnection(renderLarge.GetOutputPort())
                writer.SetFileName(out_path + str(i).zfill(3) + '.tif')
                writer.Write()
                az = naz

        # Interactive
        if interact:
            window.show(ren)

        # Generate video (requires ffmpeg)
        if video:
            log.info('Generating video from frames')
            fps = np.ceil(n_frames/12)
            subprocess.call(['ffmpeg', '-nostdin', '-y', '-framerate', str(fps),
                             '-loglevel', 'panic', '-i', out_path+'%03d'+'.tif',
                             out_path[:-1]+'.avi'])
            # subprocess.call(['rm', '-r', out_path])

        return my_cam
    
    # In progress
    # def visualize_difference(self, spang, filename='out.pdf'):
    #     import pdb; pdb.set_trace()
    #     # Take sft
    #     base_sh = np.
        
    #     radii = np.einsum('vj,pj->vp', self.Binv.T, sh) # Radii
    #     index = np.argmax(masked_radii, axis=0)
    #     peak_dirs = vertices[index]

    #     # Find peak

    #     # Print both peaks
    #     ptr = np.round(pt, 3)
    #     ptr2 = np.round(pt2, 3)
    #     if np.dot(ptr, [1,1,1]) > 0:
    #         if np.dot(ptr2, [1,1,1]) < 0:
    #             ptr2 = -ptr2
    #         print('myline('+str(ptr[0])+','+str(ptr[1])+','+str(ptr[2])+','+
    #               str(ptr2[0])+','+str(ptr2[1])+','+str(ptr2[2])+');')

