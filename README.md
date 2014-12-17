downloadboob
============

This script can be used to automatically download videos matching some criteria.

Purpose
-------

For each entry in the configuration file, the script :
- check for new video
- download the new videos
- Store the video in root_directory/entry_directory/video.name.avi

To avoid to download a video twice, all videos are stored in root_directory/.files/backend_name/video.id.avi.
The contents of root_directory/entry_directory/ will be links to those file.

If kodi is asked then 
- the video files will be prefixed with "S00E00 - "
- a file.nfo  is generated along the video file
- a file tvshow.nfo is generated
- links are replaced by the actual video file (kodi doesn't like links)
- files in root_directory/.files/backend_name/ are empty files used to not download a video twice

Dependencies
------------
- Linux
- ffmpeg or avconv
- curl or wget
- weboob
- have installed the backends you want to use :
   - videoob backend list-modules : gives the list of available backends
   - videoob backend add backend_name : install the backend backen_name
- A configuration file :
   - /etc/downloadboob.conf
   - ~/downloadboob.conf
   - ./downloadboob.conf


Parameters
----------

The main parameters are 
<table>
  <tr>
    <th>Parameter</th><th>Type   </th><th>Default value</th><th>Meaning</th>
  </tr>
  <tr>
    <td>directory</td><td>String </td><td>None         </td><td>Path to the root directory e.g. ~/Podcasts</td>
  </tr>
  <tr>
    <td>live     </td><td>Boolean</td><td>False        </td><td> - If set to True, it will generate m3u files in order to whatch the online content
  </tr>
  <tr>
    <td>         </td><td>       </td><td>             </td><td> - If set to False, it will download the online content and eventually convert the m3u files in video files.</td>
  </tr>
  <tr>
    <td>kodi         </td><td>Boolean</td><td>False        </td><td>Do you want to integrate your library in kodi (formerly XBMC) ?</td>
  </tr>
</table> 


For each entry the parameters are 
<table>
  <tr>
    <th>Parameter    </th><th>Type   </th><th>Default value</th><th>Meaning</th>
  </tr>
  <tr>
    <td>action       </td><td>String </td><td>search       </td><td>How to list available videos. Equivalent of videoob action pattern. Can be "search" or "ls"</td>
  </tr>
  <tr>
    <td>backend      </td><td>String </td><td>None         </td><td>Name of the backend to be interogated.</td>
  </tr>
  <tr>
    <td>pattern      </td><td>String </td><td>None         </td><td>What are you looking for ?</td>
  </tr>
  <tr>
    <td>directory    </td><td>String </td><td>None         </td><td>directory where the videos will be available (relative to root directory)</td>
  </tr>
  <tr>
    <td>title_regexp </td><td>String </td><td>None         </td><td>If present, the video title have to satisfy this regexp</td>
  </tr>
  <tr>
    <td>title_exclude</td><td>String </td><td>None         </td><td>If present, the video title and description must not satisfy this regexp</td>
  </tr>
  <tr>
    <td>author_regexp</td><td>String </td><td>None         </td><td>If present, the video author have to satisfy this regexp</td>
  </tr>
  <tr>
    <td>id_regexp    </td><td>String </td><td>None         </td><td>If present, the video id have to satisfy this regexp</td>
  </tr>
  <tr>
    <td>max_results  </td><td>Integer</td><td>None         </td><td>If present, only look in the first max_results elements of the list</td>
  </tr>
</table> 

Future
------

- Refactorization
- Parallelization
- Rss ?
- Podcasts ?




