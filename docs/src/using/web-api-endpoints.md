# Web API endpoints

!!! warning "Unverified"

    This is from the old documentation and needs verification.  
    It may contain errors, bugs or outdated information.

This page lists all API endpoints and their functions. An API key is required to use the API. See [API key creation](setup.md#api-key-creation) for information
on how to do that.

---

#### /submit/file

Create a new file analysis.

Method: **POST**

Data type: **form**

##### Fields

- `file`

    - The file to create the analysis with.

- `settings` (optional)

    - A JSON dictionary which can contain:
      - `timeout` (Integer) - The task timeout in seconds to use.
      - `priority` (Integer) - The priority tasks for this analysis should get. A higher number means a higher priority.
      - `platforms` (list of dictionaries). 

         Each dictionary must at least contain the keys: `platform` (string), `os_version` (string).
         
         Each entry can optionally contain:
         
         - `tags` (list of strings). - A task will be created for each platform in the platforms list.
         - `settings` (Dictionary). This dictionary supports setting a specific `browser`, `command`, and `route` per selected platform.


      - `extrpath` (list of strings). A list of paths to extract that leads to the file that should be selected.
        
         A list of paths to indicate what file should be selected for the analysis if an archive is submitted. If the file is in a nested archive, each path must be a path to the next archive. The last path must be the path to the file that should be selected.

         Example: We have an archive containing a dir1, which contains a zipfile nested.zip that contains dir2 with file.exe. The extrpath would be:
         
            `["dir1/nested.zip", "dir2/file.exe"]`
         
      - `orig_filename` (Boolean) - Ignore the filetype identified by the identification stage.
      - `browser` (String) - The browser to use for a submitted URL.

         Can only be used if one or more analysis machines have a `browser_<name>` tag. Example: setting browser to chrome will result in a 
         search for a machine with the `browser_chrome` tag.

      - `command` (list of strings) - The launch command to use when starting the submitted target.

         The `%PAYLOAD%` placeholder can be used where the filename should be on start. It is automatically replaced.
         Example to run a specific function from a submitted dll: `["rundll32.exe", "%PAYLOAD%,funcname"]`

      - `route` (Dictionary) The type of [network routing](../../installation/routing.md#automatic-per-task-routing-by-cuckoo-rooter) to use.

         The route dictionary must contain `type` (string) key containing the routing type. It optionally have an `options` (dictionary) key that contains options such as a chosen country for a VPN.

##### Example

```bash
curl http://127.0.0.1:8090/submit/file -H "Authorization: token <api key>" \
-F "file=@sample.exe" \
-F 'settings={"platforms": [{"platform": "windows": "os_version": "10"}], "timeout": 120}'
```


##### Response

Type: **JSON**

Fields:

- `analysis_id` - The identifier of the created analysis
- `settings` - The settings used for the created analysis

###### Status codes

- `200` - Successful analysis creation
- `400` - One or more of the supplied fields contains invalid data
- `503` - Analysis was created, but Cuckoo was not notified of the new analysis because Cuckoo is not running.

---

#### /submit/url

Create a new URL analysis.

Method: **POST**

Data type: **form**

##### Fields

- `url`

    - The url to create the analysis with.

- `settings`

   - A JSON dictionary which can contain:
      - `timeout` (Integer) - The task timeout in seconds to use.
      - `priority` (Integer) - The priority tasks for this analysis should get. A higher number means a higher priority.
      - `platforms` (list of dictionaries). 

         Each dictionary must at least contain the keys: `platform` (string), `os_version` (string).
         Each entry can optionally contain:
         
         - `tags` (list of strings). 
         - `settings` (Dictionary). This dictionary supports setting a specific `route` per selected platform.
         
         A task will be created for each platform in the platforms list.

      - `route` (Dictionary) The type of [network routing](../../installation/routing.md#automatic-per-task-routing-by-cuckoo-rooter) to use.

         The route dictionary must contain `type` (string) key containing the routing type. It optionally have an `options` (dictionary) key that contains options such as a chosen country for a VPN.

##### Example

```bash
curl http://127.0.0.1:8090/submit/file -H "Authorization: token <api key>" \
-F "url=http://example.com" \
-F 'settings={"platforms": [{"platform": "windows", "os_version": "10"}], "timeout": 120}'
```


##### Response

Type: **JSON**

Fields:

- `analysis_id` - The identifier of the created analysis
- `settings` - The settings used for the created analysis

###### Status codes

- `200` - Successful analysis creation
- `400` - One or more of the supplied fields contains invalid data
- `503` - Analysis was created, but Cuckoo was not notified of the new analysis because Cuckoo is not running.

---

#### /submit/platforms

Get a dictionary of all platforms and the versions available.

Method: **GET**

##### Example

```bash
curl http://127.0.0.1:8090/submit/platforms -H "Authorization: token <api key>"
```


##### Response

Type: **JSON**

```json
{
   "windows" : ["10", "7"]
}
```

###### Status codes
- `200` - Successful query


---

#### /submit/browsers

Get a list of all supported browsers. This list is populated by finding machines with
specific machine tags. See [machinery machine config fields](../../installation/vmcreation.md#machinery-config-machines-fields) for more information.

Method: **GET**

##### Example

```bash
curl http://127.0.0.1:8090/submit/browsers -H "Authorization: token <api key>"
```


##### Response

Type: **JSON**

```json
["internet explorer"]
```

###### Status codes
- `200` - Successful query

---

#### /submit/routes

Get a list of all supported routes. This will only be populated if [Cuckoo rooter](../../installation/routing.md#cuckoo-rooter) is used.

Method: **GET**

##### Example

```bash
curl http://127.0.0.1:8090/submit/routes -H "Authorization: token <api key>"
```


##### Response

Type: **JSON**

```json
{
   "available":[
      "vpn",
      "drop",
      "internet"
   ],
   "vpn":{
      "countries":[
         "france",
         "germany"
      ]
   }
}
```

###### Status codes
- `200` - Successful query

---

#### /analyses/

Get a list of existing analyses. Each analysis will contain the analysis state, score and its target.

Method: **GET**

##### GET parameters

- `limit` (Integer) - The maximum amount of analyses to return. 20 by default.
- `offset` (Integer) -  The offset of the analyses list. 0 by default.
- `desc` (Boolean) - Order analyses descending by date. True by default.

##### Example

```bash
curl http://127.0.0.1:8090/analyses/ -H "Authorization: token <api key>" \

```

##### Response

Type: **JSON**

```json
{
   "offset" : 0,
   "analyses" : [
      {
         "location" : null,
         "target" : {
            "sha1" : "7185a9fd0140a752db4fcabb09c863209787b8d8",
            "category" : "file",
            "sha256" : "cbdb56e796b3fefb8c911e4f9237047d2d805dceccbea3dbac1ff87328e5f425",
            "md5" : "d9ea2b4a5f6613d624e9ee0eee44c232",
            "media_type" : "application/x-dosexec",
            "sha512" : "",
            "analysis_id" : "20210707-6UZJTX",
            "target" : "fx13ttg_138028.exe"
         },
         "kind" : "standard",
         "state" : "finished",
         "priority" : 1,
         "created_on" : "2021-07-07T16:01:11.028462",
         "id" : "20210707-6UZJTX",
         "score" : 10
      }
   ],
   "limit" : 20,
   "desc" : true
}

```


###### Status codes
- `200` - Successful query

---

#### /analysis/(analysis id)

Retrieve the full analysis information for the specified analysis id.

Method: **GET**

##### Example

```bash
curl http://127.0.0.1:8090/analysis/20210707-6UZJTX -H "Authorization: token <api key>" \

```


##### Response

Type: **JSON**


<details>
  <summary>Click to view response</summary>
  
```json
{%
 include-markdown "./analysis.json"
 comments=false
%}
```
</details>

###### Status codes

- `200` - Successful query

---

#### /analysis/(analysis id)/identification

Retrieve the file identification json for the specified analysis id.

Method: **GET**


##### Example

```bash
curl http://127.0.0.1:8090/analysis/20210707-6UZJTX/identification -H "Authorization: token <api key>"
```


##### Response

Type: **JSON**

```json
{
   "selected" : true,
   "identified" : true,
   "ignored" : [],
   "errors" : {},
   "target" : {
      "machine_tags" : [],
      "container" : false,
      "sha1" : "7185a9fd0140a752db4fcabb09c863209787b8d8",
      "orig_filename" : "fx13ttg_138028.exe",
      "sha256" : "cbdb56e796b3fefb8c911e4f9237047d2d805dceccbea3dbac1ff87328e5f425",
      "extrpath" : [],
      "md5" : "d9ea2b4a5f6613d624e9ee0eee44c232",
      "password" : "",
      "size" : 393216,
      "platforms" : [
         {
            "os_version" : "",
            "platform" : "windows"
         }
      ],
      "media_type" : "application/x-dosexec",
      "filetype" : "PE32 executable (GUI) Intel 80386, for MS Windows",
      "filename" : "fx13ttg_138028.exe"
   },
   "category" : "file"
}
```


###### Status codes

- `200` - Successful query


---

#### /analysis/(analysis id)/pre

Retrieve the static/pre stage report for the specified analysis.

Method: **GET**

##### Example

```bash
curl http://127.0.0.1:8090/analysis/20210707-6UZJTX/pre -H "Authorization: token <api key>"
```


##### Response

Type: **JSON**

<details>
  <summary>Click to view response</summary>
  
```json
{%
 include-markdown "./pre.json"
 comments=false
%}
```
</details>


###### Status codes

- `200` - Successful query

---

#### /analysis/(analysis id)/submittedfile

Download the submitted file for the specified analysis.

Method: **GET**

##### Example

```bash
curl http://127.0.0.1:8090/analysis/20210707-6UZJTX/submittedfile -JO -H "Authorization: token <api key>"
```


##### Response

Type: **File**



###### Status codes

- `200` - Successful query

---

#### /analysis/(analysis id)/task/(task id)

Retrieve the task information JSON for the specified task id.

Method: **GET**

##### Example

```bash
curl http://127.0.0.1:8090/analysis/20210707-6UZJTX/task/20210707-6UZJTX_1 -H "Authorization: token <api key>"
```


##### Response

Type: **JSON**

```json
{
   "machine" : "",
   "machine_tags" : [],
   "number" : 1,
   "errors" : {},
   "os_version" : "10",
   "kind" : "standard",
   "platform" : "windows",
   "id" : "20210707-6UZJTX_1",
   "score" : 10,
   "state" : "reported",
   "analysis_id" : "20210707-6UZJTX"
}
```

###### Status codes

- `200` - Successful query

---

#### /analysis/(analysis id)/task/(task id)/machine

Retrieve the used analysis machine information of the specified task id.

Method: **GET**

##### Example

```bash
curl http://127.0.0.1:8090/analysis/20210707-6UZJTX/task/20210707-6UZJTX_1/machine -H "Authorization: token <api key>"
```


##### Response

Type: **JSON**

```json
{
   "ip" : "192.168.122.101",
   "reserved" : false,
   "errors" : [],
   "mac_address" : "",
   "machinery_name" : "kvm",
   "state" : "poweroff",
   "name" : "win10x64_1",
   "disabled" : false,
   "disabled_reason" : "",
   "locked_by" : "20210707-6UZJTX_1",
   "tags" : [
      "exampletag1",
      "exampletag2"
   ],
   "platform" : "windows",
   "snapshot" : null,
   "reserved_by" : "",
   "locked" : true,
   "label" : "win10x64_1",
   "os_version" : "10"
}
```

###### Status codes

- `200` - Successful query

---

#### /analysis/(analysis id)/task/(task id)/post

Retrieve the behavioral analysis/post stage report of the specified task id.

Method: **GET**

##### Example

```bash
curl http://127.0.0.1:8090/analysis/20210707-6UZJTX/task/20210707-6UZJTX_1/post -H "Authorization: token <api key>"
```

##### Response

Type: **JSON**

<details>
  <summary>Click to view response</summary>
  
```json
{%
 include-markdown "./post.json"
 comments=false
%}
```
</details>


###### Status codes

- `200` - Successful query

---

#### /analysis/(analysis id)/task/(task id)/pcap

Download the PCAP file of the specified task id.

Method: **GET**

##### Example

```bash
curl http://127.0.0.1:8090/analysis/20210707-6UZJTX/task/20210707-6UZJTX_1/pcap -JO -H "Authorization: token <api key>"
```

##### Response

Type: **File**

###### Status codes

- `200` - Successful query

---

#### /analysis/(analysis id)/task/(task id)/screenshot/(screenshot name)

Download the specified screenshot. The available screenshots are listed in the post report.

Method: **GET**

##### Example

```bash
curl http://127.0.0.1:8090/analysis/20210707-6UZJTX/task/20210707-6UZJTX_1/screenshot/44997.jpg -JO -H "Authorization: token <api key>"
```

##### Response

Type: **File**

###### Status codes

- `200` - Successful query


#### /targets/file/(sha256 hash)

Download a file that was submitted or ever selected as a target.

Method: **GET**

##### Example

```bash
curl http://127.0.0.1:8090/targets/file/81de431987304676134138705fc1c21188ad7f27edf6b77a6551aa693194485e -JO -H "Authorization: token <api key>"
```

##### Response

Type: **File**

###### Status codes

- `200` - Successful query
