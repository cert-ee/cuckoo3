# Virtual machine creation

## TLDR

```bash
vmcloak --debug init --win10x64 --hddsize 128 --cpus 2 --ramsize 4096 --network 192.168.30.0/24 --vm qemu --vrde --vrde-port 1 --ip 192.168.30.2 --iso-mount /mnt/win10x64 win10base qemubr0 && \
vmcloak --debug install win10base --recommended && \
vmcloak --debug snapshot --count 1 win10base win10vm_ 192.168.30.10
```

The virtual machines are environments in which samples are detonated. This page
describes the requirements that each created virtual machine must have.

## Overview

This section describes how to create, install software on and make snapshots 
of virtual machines.

### Network

The analysis machine must have their own network and default gateway. The 
default gateway is where Cuckoo3 will start the network capture for traffic from 
and to a specific machine.  
VMCloak will handle assigning unique IPs to each snapshot.

#### Network guidelines and advice

- For the best analysis results, analysis machine should be able to reach the 
internet.
- Analysis VMs should not be able to reach other host ports other than the 
result server one.

## Creating an image 

### Requirements

!!! note "Requirements"

    Before proceeding, make sure that you have:  

    - VMCloak installed - [Install VMCloak](../installing/vmcloak.md){:target=_blank}
    - downloaded preferred image - [Downloading an image](../installing/vmcloak.md#downloading-an-image){:target=_blank}  
    - created a network interface and mount - [Configuration](../installing/vmcloak.md#configuring-vmcloak){:target=_blank}
        - You can use the script in VMCloak directory if you closed the terminal
        and bridge is no longer available or win10x64 got unmounted.

An image is the disk where we install the chosen OS on. Any dependencies we 
choose are also installed on this. 
When we have made all modification we want, we make the VMs from this image. 
After this, the image must not be edited.

1. To create the image, run:

        vmcloak --debug init --win10x64 --hddsize 128 --cpus 2 --ramsize 4096 --network 192.168.30.0/24 --vm qemu --vrde --vrde-port 1 --ip 192.168.30.2 --iso-mount /mnt/win10x64 win10base qemubr0

2. To install software, run :

        vmcloak --debug install win10base --recommended

3. (Optional) To install custom software, run:  
(check [Usage / dependencies](#usage) for full list of installable software)

        vmcloak --debug install win10base office office.version=2010 office.isopath=/home/cuckoo/office2010.iso office.serialkey=XXXXX-XXXXX-XXXXX-XXXXX-XXXXX office.activate=1

4. To make snapshots, run:

        vmcloak --debug snapshot --count 1 win10base win10vm_ 192.168.30.10

Snapshots will be stored in `~/.vmcloak/vms/qemu/` directory.

### Recommended installation

VMCloak `--recommended` option in `vmcloak install` does the following:

- **Installs**:
    - ie11
    - .NET
    - Java
    - VC redistributables 2013-2019
    - Edge
    - Adobe PDF, 
- **Modifies**:
    - updates (Let’s encrypt) root certs
    - a wallpaper
    - OS optimization (stopping updates, removing unneeded components)
    - disable unneeded services such as Cortana

This can all be viewed afterwards with the list image command.

---

## Adding machines to Cuckoo

For detailed description of how to manage Cuckoo3 vms, please refer to 
[Cuckoo3 VM configuration](../installing/cuckoo.md#vms){:target=_blank}.

## Usage

<details>
<summary>dependencies</summary>

```bash
vmcloak list deps

Name version target sha1 arch

acpishutdown
--------------------
adobe9
adobe9  9.0.0   None 8faabd08289b9a88023f71136f13fc4bd3290ef0 
adobe9  9.1.0   None 1e0db06c84d89c8f58b543a41ec35b133de7ea19 
adobe9  9.2.0   None 4b6207b018cf2be2f49d1f045ff369eb3bee88da 
adobe9  9.3.0   None 98cacd6069e78a0dd1ef87ce24e59716fecf8aa0 
adobe9  9.3.3   None b1ed1d350db97ddd562606449804e705d4ffe1c7 
adobe9  9.3.4   None e3bb8eff9d199ab1f4b5f7a10e514a74e0384ca0 
adobe9  9.4.0   None 4652a454056b2323097a6357292db3af239bb610 
adobe9  9.5.0   None e46000691a6dbcd7892078b46c8ee13613683545 
adobe9  10.1.4  None fe6808d5d11e94dc5581f33ed386ce552f0c84d6 
adobe9  11.0.0  None e7dd04e037c40b160a2f01db438dba9ea0b12c52 
adobe9  11.0.2  None e1d9e57f08e169fb1c925f8ded93e5f5efe5cda3 
adobe9  11.0.3  None 9c2b6903b000ecf2869e1555bc6e1b287e6176bf 
adobe9  11.0.4  None 9c295c16d374735bf292ef6c630c9ab392c22500 
adobe9  11.0.6  None 6a3d5b494b4ed6e11fc7d917afc03eaf05d4a6aa 
adobe9  11.0.7  None 3e08c3f6daad59f463227590cc438b3906648f5e 
adobe9 * 11.0.8  None 3e889258ea2000337bbe180d81317d44f617a292 
adobe9  11.0.9  None 53b367bff07a63ee07cf1cd090360b75d3fc6bfb 
adobe9  11.0.10 None 98b2b838e6c4663fefdfd341dfdc596b1eff355c 
adobe9  11.0.11 None 182eb5b4ca71e364f62e412cdaec65e7937417e4 
adobe9  11.0.12 None c5a5f2727dd7dabe0fcf96ace644751ac27872e7 
adobe9  11.0.13 None 89317596ffe50e35c136ef204ac911cbf83b14d9 
adobe9  11.0.14 None d7b990117d8a6bbc4380663b7090cd60d2103079 
adobe9  11.0.16 None ca825c50ed96a2fec6056c94c1bb44eedbaed890 
adobe9  11.0.17 None c5fe501856be635566e864fe76f6d6a7ff3874ca 
adobe9  11.0.18 None 420d64c064cd9904836a60066a222c64b0ea060e 
adobe9  11.0.19 None 98fdf7a15fb2486ee7257767296d4f7a0a62ac92 
--------------------
adobepdf
adobepdf  9.0.0   None 8faabd08289b9a88023f71136f13fc4bd3290ef0 
adobepdf  9.1.0   None 1e0db06c84d89c8f58b543a41ec35b133de7ea19 
adobepdf  9.2.0   None 4b6207b018cf2be2f49d1f045ff369eb3bee88da 
adobepdf  9.3.0   None 98cacd6069e78a0dd1ef87ce24e59716fecf8aa0 
adobepdf  9.3.3   None b1ed1d350db97ddd562606449804e705d4ffe1c7 
adobepdf  9.3.4   None e3bb8eff9d199ab1f4b5f7a10e514a74e0384ca0 
adobepdf  9.4.0   None 4652a454056b2323097a6357292db3af239bb610 
adobepdf  9.5.0   None e46000691a6dbcd7892078b46c8ee13613683545 
adobepdf  10.1.4  None fe6808d5d11e94dc5581f33ed386ce552f0c84d6 
adobepdf  11.0.0  None e7dd04e037c40b160a2f01db438dba9ea0b12c52 
adobepdf  11.0.2  None e1d9e57f08e169fb1c925f8ded93e5f5efe5cda3 
adobepdf  11.0.3  None 9c2b6903b000ecf2869e1555bc6e1b287e6176bf 
adobepdf  11.0.4  None 9c295c16d374735bf292ef6c630c9ab392c22500 
adobepdf  11.0.6  None 6a3d5b494b4ed6e11fc7d917afc03eaf05d4a6aa 
adobepdf  11.0.7  None 3e08c3f6daad59f463227590cc438b3906648f5e 
adobepdf * 11.0.8  None 3e889258ea2000337bbe180d81317d44f617a292 
adobepdf  11.0.9  None 53b367bff07a63ee07cf1cd090360b75d3fc6bfb 
adobepdf  11.0.10 None 98b2b838e6c4663fefdfd341dfdc596b1eff355c 
adobepdf  11.0.11 None 182eb5b4ca71e364f62e412cdaec65e7937417e4 
adobepdf  11.0.12 None c5a5f2727dd7dabe0fcf96ace644751ac27872e7 
adobepdf  11.0.13 None 89317596ffe50e35c136ef204ac911cbf83b14d9 
adobepdf  11.0.14 None d7b990117d8a6bbc4380663b7090cd60d2103079 
adobepdf  11.0.16 None ca825c50ed96a2fec6056c94c1bb44eedbaed890 
adobepdf  11.0.17 None c5fe501856be635566e864fe76f6d6a7ff3874ca 
adobepdf  11.0.18 None 420d64c064cd9904836a60066a222c64b0ea060e 
adobepdf  11.0.19 None 98fdf7a15fb2486ee7257767296d4f7a0a62ac92 
--------------------
bootpolicy
--------------------
carootcert
--------------------
chrome
chrome * 46.0.2490.80 None a0ade494dda8911eeb68c9294c2dd0e3229d8f02 
chrome  latest       None None x86
chrome  latest       None None amd64
--------------------
cuteftp
cuteftp * 9.0.5 None 1d8497b3f31f76168eb2573efe60dcefb3422e1d 
--------------------
disableservices
--------------------
dns
--------------------
dotnet
dotnet  4.0   None 58da3d74db353aad03588cbb5cea8234166d8b99 
dotnet  4.5   None b2ff712ca0947040ca0b8e9bd7436a3c3524bb5d 
dotnet  4.5.1 None 5934dd101414bbc0b7f1ee2780d2fc8b9bec5c4d 
dotnet  4.5.2 None 89f86f9522dc7a8a965facce839abb790a285a63 
dotnet  4.6   None 3049a85843eaf65e89e2336d5fe6e85e416797be 
dotnet  4.6.1 None 83d048d171ff44a3cad9b422137656f585295866 
dotnet  4.6.2 None a70f856bda33d45ad0a8ad035f73092441715431 
dotnet  4.7   None 76054141a492ba307595250bda05ad4e0694cdc3 
dotnet * 4.7.2 None 31fc0d305a6f651c9e892c98eb10997ae885eb1e 
--------------------
dotnet40
dotnet40  4.0   None 58da3d74db353aad03588cbb5cea8234166d8b99 
dotnet40  4.5   None b2ff712ca0947040ca0b8e9bd7436a3c3524bb5d 
dotnet40  4.5.1 None 5934dd101414bbc0b7f1ee2780d2fc8b9bec5c4d 
dotnet40  4.5.2 None 89f86f9522dc7a8a965facce839abb790a285a63 
dotnet40  4.6   None 3049a85843eaf65e89e2336d5fe6e85e416797be 
dotnet40  4.6.1 None 83d048d171ff44a3cad9b422137656f585295866 
dotnet40  4.6.2 None a70f856bda33d45ad0a8ad035f73092441715431 
dotnet40  4.7   None 76054141a492ba307595250bda05ad4e0694cdc3 
dotnet40 * 4.7.2 None 31fc0d305a6f651c9e892c98eb10997ae885eb1e 
--------------------
edge
--------------------
extract
--------------------
finalize
--------------------
firefox
firefox * 41.0.2 None c5118ca76f0cf6ecda5d2b9292bf191525c9627a 
firefox  60.0.2 None 565c5ddca3e4acbc30a550f312d3a1a7fd8d8bce 
firefox  63.0.3 None c5f03fc93aebd2db9da14ba6eb1f01e98e18d95b 
--------------------
firefox_41
firefox_41 * 41.0.2 None c5118ca76f0cf6ecda5d2b9292bf191525c9627a 
firefox_41  60.0.2 None 565c5ddca3e4acbc30a550f312d3a1a7fd8d8bce 
firefox_41  63.0.3 None c5f03fc93aebd2db9da14ba6eb1f01e98e18d95b 
--------------------
flash
flash  11.4.402.287 None 99fb61ed221df9125698e78d659ee1fc93b97c60 
flash  11.6.602.168 None 906f920563403ace6dee9b0cff982ea02d4b5c06 
flash * 11.7.700.169 None 790b09c63c44f0eafd7151096bf58964857d3b17 
flash  11.8.800.94  None f7a152aa3af4a7bbef4f87ab5e05d24824ddf439 
flash  11.8.800.174 None f3a466b33e11a72f3bef4ecd40ef63c19f97a077 
flash  11.9.900.117 None 982cf5626174e42814a7bb27ff62378b230dc201 
flash  11.9.900.170 None 877c7e9a6de692bdef95a4f3cc22b9fb385db92e 
flash  12.0.0.38    None e44908c9a813876c1a332a174b2e3e9dff47a4ff 
flash  13.0.0.182   None fbe7a2698da29284be8366adaf8765e9990fd6e0 
flash  13.0.0.214   None c79bfbb23b497cec805164df9f038644d74476aa 
flash  14.0.0.125   None f6bd2b5e91195182898828cc1235fd27d2aa8d55 
flash  15.0.0.167   None 79f04ea94d033c07e7cc889751769e98f99d23fb 
flash  15.0.0.189   None 8bfd539853e0db0a58efdb8c5f5c021f1fcb9f8d 
flash  16.0.0.235   None ad3da00825193ecee48440203b6051310f4de3b7 
flash  18.0.0.194   None 2611f2d81ea8ef747f079d797099da89648566ed 
flash  18.0.0.203   None 98ab0531be9f2b49adeb56c621678c17455e6f66 
flash  18.0.0.209   None a209b6a320965cfbd75455ee79ab28e03bd5371c 
flash  19.0.0.207   None 9a901f938add920ed846ae18187176cbdb40ecfb 
flash  19.0.0.245   None 1efef336190b021f6df3325f958f1698a91cce8c 
flash  20.0.0.228   None fa86f107111fc7def35742097bf0aa29c82d7638 
flash  20.0.0.286   None a1b73c662b7bce03ff2d8a729005e81036ea1a24 
flash  20.0.0.306   None 68ae4277d68146749cb6cf597d3d6be07422c372 
flash  21.0.0.182   None 717582fc7138c9cf4b3ec88413d38cddf8613d4c 
flash  21.0.0.197   None 1e81a4617abcbb95ee6bf9250be5a205ce0d289b 
flash  21.0.0.213   None 6d23ae1f12682b6baa1833c12955ca9adf7d13f2 
flash  21.0.0.242   None 01261660476cdcacf1872a8a5142018bce6de1dc 
flash  22.0.0.192   None 6aba77bca04f7170ac90c3852b837027f840b051 
flash  22.0.0.209   None 7db31a028cf14bdcdb4374fd941c08412130e384 
flash  23.0.0.162   None 4408e4b6c9ced6490d2b0b81d6a62d00776c8042 
flash  23.0.0.185   None b86c4a79c445481992ac41c47a22323068ca40b1 
flash  23.0.0.205   None c329a24860028263631411bd1c37369022473e9a 
flash  23.0.0.207   None 699097fa5bbc4d3a0a9733108678ee642d1cc667 
flash  24.0.0.186   None f9828b0e872f71879664078dbaa23b05fff47494 
flash  24.0.0.194   None 2d9648adf6fdc05cbc61b037ec5e434c7a73dfe4 
flash  24.0.0.221   None e8ac1c9c4e12ce7164b1f7374e6ef2868ab51e7f 
flash  25.0.0.127   None 78618c96a0e65cc1ace1aedb0ecac04972b3ac7f 
flash  25.0.0.148   None e3907d0e0ac26a2db556ee6fa864243f3cb0a9f0 
flash  25.0.0.171   None 780af04828e234a59ed297bcd31e4a08a0ce3364 
flash  26.0.0.126   None 40dda6ea0f2a191a027fc6d4a61d2ee98636694e 
flash  26.0.0.131   None a1b5db1a5231740b64a8833b53f481b22402b430 
flash  26.0.0.137   None c7230247b1f1622016c38e4bedfdace9e49c6379 
flash  26.0.0.151   None 6ebfb96f7c4c4c3d54a183cffaaa712c799982a5 
flash  27.0.0.130   None a37f295cc346912d959631f5301255790b495870 
flash  27.0.0.159   None fe243a4d9237b054346a750697eb25ed897492e7 
flash  27.0.0.170   None bf376fe52e6441a98c1a5b0686c11faf879af557 
flash  27.0.0.183   None f617731fce561af0451433daba4bc6b90c7673dd 
flash  27.0.0.187   None 4c1e4dc52fbe26f53844cbbf18c5c3675c203895 
flash  28.0.0.126   None 6ce0b7e7f813f32c51d34e454f19dc85529bc93f 
flash  28.0.0.137   None addd5ad5be2ae11868d2c8bcefd9396a30329fee 
flash  28.0.0.161   None 240fec89d632534f1231475beee8eb4466b784b0 
flash  29.0.0.113   None cea86cb70ee72b7b968b94106b8ba2d231fd0a2b 
flash  29.0.0.140   None ed2d4358477b393438f455a7283d583fc98ef073 
flash  29.0.0.171   None f23fc2d65dd38efc3ce15f44e2c21118db65ede0 
flash  30.0.0.113   None 9179639901137aeb153b737cb60554fe183757f1 
flash  30.0.0.134   None d8d922c8bc2b3604aa1b51455d99181a6e84b973 
flash  30.0.0.154   None a3434a3d95d10bf9ab1ba08c8054749d25f93733 
flash  31.0.0.108   None c01a59040a1e707e1235c40defd7cafafe534bc6 
flash  31.0.0.122   None c831ab890facb906dc3608058cd3269919c39076 
flash  31.0.0.148   None a8cc46cc58195b03322dc0588ce692f2e4c97948 
flash  31.0.0.153   None 23bf7580af5abb6e6717b94d8543a1f88bfb4992 
flash  32.0.0.101   None b5fb393a4ce018d0c1b094075f6dcbd72a72fa65 
flash  32.0.0.114   None 5d74603b8156921b87720f8cdf6a9b95334b0cb6 
flash  32.0.0.142   None 0682aae6e00ea3af2fd0702c1cb22d132d8f0e9b 
flash  32.0.0.156   None b7bb0248c95d5235faab09e73e9a7454a0a86c03 
flash  latest       None None 
--------------------
ie10
ie10 * 10 win7x64 17d1eaca123e453269b12b20863fd5ce96727888 
ie10 * 10 win7x86 e6552da75de95f6b1f7937c2bdb5fe14443dea2a 
--------------------
ie11
ie11 * 11 win7x64 ddec9ddc256ffa7d97831af148f6cc45130c6857 
ie11 * 11 win7x86 fefdcdde83725e393d59f89bb5855686824d474e 
--------------------
ie9
ie9 * 9 win7x64 5ace268e2812793e2232648f62cdf4be17b2b4dd 
ie9 * 9 win7x86 fb2b17cf1d22f3e2b2ad339c5bd78f8fab406d03 
--------------------
java
java  jdk7     None 2546a78b6138466b3e23e25b5ca59f1c89c22d03 
java  7        None 0faa00705651531c831380a6af83b564b995ecb0 
java  jdk7u1   None ed434b8bc132a5bfda031428b26daf7b8331ecb9 
java  7u1      None 26ec209d66c3b21ef3c7b6c1f3b9fa52466420ed x86
java  7u1      None bd40f1dcd72326bb472cd131acb04d707566e706 amd64
java  7u2      None a36ae80b80dd1c9c5c466b3eb2451cd649613cfb 
java  jdk7u3   None fe9dc13c0a6424158dc0f13a6246a53973fb5369 
java  7u3      None 61f48fa0875c85acc8fe1476a1297212f96ea827 x86
java  7u3      None 0d74117467cd905f41fd807f7cdbaa671a150311 amd64
java  7u4      None a2e927632b2106f5efefc906ed9070d8c0bf660f 
java  jdk7u5   None 88c2fc5e5e61e7f709370c01abb138c65009307b 
java  7u5      None 504d94c7cc1617b44af8d81de6fd83120b04dfa5 x86
java  7u5      None ca01de8bf2290c9b891c0bf4aac4c099f66d80e7 amd64
java  7u6      None 09f3a1d0fe7fabd4cfdc1c23d1ed16016d064d01 
java  jdk7u7   None 58e4bdd12225379284542b161e49d8eaea4e00c2 
java  7u7      None fad4496cd61a0ef1b42c27aeb405a3739ea0943f x86
java  7u7      None 9af03460c416931bdee18c2dcebff5db50cb8cb3 amd64
java  jdk7u9   None 11a256bd791033527580c6ac8700f3a72f7f4bcf 
java  7u9      None 18c70915192bf5069543b8f95dd44f159ea6deec x86
java  7u9      None 7ae6d07324439a203af612789110691f757b980e amd64
java  jdk7u10  None f57bfa38a05433d902582fab9d08f530d7c7749b 
java  7u10     None d159c752086d6134aacb2e15a10ccaf8ef39bca0 x86
java  7u10     None 1c01773d0fd8e53af5fbf3cd2203ad6cf2545dbc amd64
java  jdk7u11  None a482e48e151cff76dcc1479b9efc367da8fb66a7 
java  7u11     None 682fb136563f08c20d37b25a28fce0883f893d8b x86
java  7u11     None 41c3af2cf67c367066863a067ce831cf80586cdb amd64
java  jdk7u13  None bd6848138385510b32897a5b04c94aa4cf2b4fca 
java  7u13     None 72ad271c6c7e7d1893a9661aad2854a75e87cd5f x86
java  7u13     None 0acc9b9d6a7f4ebd255c0cc720a6f452797c487f amd64
java  jdk7u15  None f52453c6fd665b89629e639abdb41492eff9a9e3 
java  7u15     None 5348714e363eb7df9ce5698cfcbb324e525cbd92 x86
java  7u15     None 53345cc82bee2a8ddce8dea26992f371e25f37cd amd64
java  jdk7u17  None 1f462dea65c74dd9fdf094d852e438a0e6a036bc 
java  7u17     None 7b2cd00ec4c57396642afcc463e6d895772925a8 x86
java  7u17     None eac554818507609480e8a890e232b3a8b0b2f55e amd64
java  jdk7u21  None f677efa8309e99fe3a47ea09295b977af01f2142 
java  7u21     None 620472dc1e7d015ed9a7700b846565a707946fcb x86
java  7u21     None 9ec7523c5b8f5621ae21ab2fec12597ea029bb7f amd64
java  jdk7u25  None 5eeb8869f9abcb8d575a7f75a6f85550edf680f5 
java  7u25     None 08ce588fb3668e987a0fa93becf754e9c8027d51 x86
java  7u25     None ad65e982d8ebf03bb2ddbb418aa26ab499daee41 amd64
java  jdk7u40  None b611fb48bb5071b54ef45633cd796a27d5cd0ffd 
java  7u40     None c0429dca47c0f22bbcd33492f39117245bab515d x86
java  7u40     None 85c7db9a1c432a119c90d1d1b203ccaaedae3444 amd64
java  jdk7u45  None cfd7e00fa0f6b3eef32832dd7487c6f56e7f55b8 
java  7u45     None a2269c804418186c9b944746f26e225b3e77a571 x86
java  7u45     None 155008d2cb8392befb4dcfec8afc5fd2c84173cc amd64
java  jdk7u51  None 439435a1b40053761e3a555e97befb4573c303e5 
java  7u51     None 72aa32f97a0ddd306d436ac3f13fabb841b94a76 x86
java  7u51     None 0d3346f4c249d9443237205cc1c0dde1ef534874 amd64
java  jdk7u55  None bb244a96e58724415380877230d2f6b466e9e581 
java  7u55     None 96b937f49f07068313530db491b92e7e9afb80ba x86
java  7u55     None 567c3bc32254b2235f0bc30e910323e2dd1e38aa amd64
java  jdk7u60  None 8f9185b1fb80dee64e511e222c1a9742eff7837f 
java  7u60     None 1672aed79505e52b6c39ee706d2f424910ad4493 x86
java  7u60     None 29162a9087b41a0fb2a476ebc78ae5d2ae02495a amd64
java  jdk7u65  None 9c52a8185b9931b8ae935adb63c8272cf6d9e9ba 
java  7u65     None 0eb1db8fd71552ed48099881e2bde8bd41bbe53a x86
java  7u65     None 8154af812e608bd0c8193c4d5e332a4133ed1aee amd64
java  jdk7u67  None dff04608d4c045cdd66dffe726aed27b22939c9e 
java  7u67     None cdcb564088e565b3ed56d9bc9d80448a4e3a9fc6 x86
java  7u67     None 7d9413d367faa0b096ee72c2d5f1983bb7334e9e amd64
java  jdk7u71  None 8ca5c5ad43148dfc0e5640db114e317f1bbd6a25 
java  7u71     None b04ba06f787b596c57ede7e3c0250546d0635f73 x86
java  7u71     None 714240cf53190bfccb0bb237323a2496300be946 amd64
java  7u72     None 57f7dff98bdfbe064af159bbd1d8753cad714f68 
java  jdk7u75  None 700e56c9b57f5349d4fe9ba28878973059dc68fa 
java  7u75     None cd5f2222c6a9db6adfb385eaaeff8f95ea32446f x86
java  7u75     None 488492de778fc47f67a33c65ea922124279c20d4 amd64
java  7u76     None 0469ba6302aa3dc03e39075451aef1c60e5e4114 
java  jdk7u79  None 319306c148c97f404c00e5562b11f5f4ea5fd6e5 
java  7u79     None b062b03a04e0f3ce222282ca1760e4234d3c6f1f x86
java  7u79     None 6e407b926eaf023e4248fdfffa810ded9d4ac7a3 amd64
java * 7u80     None aebbc0b02c16e7169b0577962fa91c613f8a7a45 
java  8        None 09a05b1afad97ffa35a47d571752c3e804c200c7 
java  jdk8u5   None 81660732a53e08651c633d99b0e6042cbbaf616d 
java  8u5      None ca48401f6f71ad360b3c0882393e2c93c35f80de x86
java  8u5      None ca656e8a722c068939665ad23760b8b072281594 amd64
java  8u11     None 757103707b16e6a79ebd4d134613e483007a0c7a 
java  8u20     None 30df3349f710e6b54adccadadc1e1f939ab2f6da 
java  jdk8u25  None 79b4b68aea5ef6448c39c2ee3103722db6548ff0 
java  8u25     None ff3d21c97e9ca71157f12221ccf0788a9775ec92 x86
java  8u25     None 73024362b55d35f77562f203faba892c7540b68d amd64
java  jdk8u31  None 5b8a1f8d11ecbcd46ed3389498ef67a4f699133b 
java  8u31     None b8ef84ba6a68c35b5d7a5304b4c0304aa53858b8 x86
java  8u31     None 00b5d23743d097d9b8f50bd14602bf4bae525b00 amd64
java  jdk8u40  None ff9f4d62dffa0a81abbc0e5e151586301ddf4884 
java  8u40     None c583ea81fe3cf6b06e2851f6805ec895226a0053 x86
java  8u40     None 3034ee9474c8829cb9145f3ceadf4e4f8618b9f8 amd64
java  jdk8u45  None 8e839fe0e30a56784566017f6acdb0fbe213c8bc 
java  8u45     None 7fc89bd7f82a092d2aa15b753f1fa17e47b879aa x86
java  8u45     None 4d71c0fccdad64149da2edbd89b8871c83ad5f7e amd64
java  jdk8u51  None 0aaee8ff5f62fdcb3685d513be471c49824d7e04 
java  8u51     None e0e42aaeedbb77a19809004a576496dcdcf99ed5 x86
java  8u51     None 447fd1f59219282ec5d2f7a179ac12cc072171c3 amd64
java  jdk8u60  None 47b36bc0fdc44029f82a50346fbb85b8f7803d7f 
java  8u60     None bd486f62bc358b1180218480a1cbb0a42483af98 x86
java  8u60     None 87976e29f58276685c63833ae42df7b2b5fe921c amd64
java  jdk8u65  None 66bdacc1252f309f157fd0786d2e148dbb394629 
java  8u65     None 5e0b4ef55faf1de9b4b85d769bfe0899481c5d79 x86
java  8u65     None 85a8021af3299e5bc439a071e8b2cea6a137c6ad amd64
java  jdk8u66  None 0013f600723a1a16aa97f7c3fbe1c27fd7674cbe 
java  8u66     None b35523fe8891f4f29942482b0b9a205801294595 x86
java  8u66     None b5a1871e28ab78aa0d48f0d61b3e03e98db50510 amd64
java  jdk8u71  None c6726fb46cb40b42b4b545502ee87172b7d290f5 
java  8u71     None 42db2fbd719a173f6d6d81bbb05f4033628c798c x86
java  8u71     None 7875f835edf7383b221ca7a4f6b81072727f6eed amd64
java  8u72     None d1b6e793c21f1bec935f647ec49a12bc54109ace 
java  jdk8u73  None f56e21ece567f42fce5a38961bd81288dd2956c0 
java  8u73     None 77551adf49d25bcbd3f9217190a87df8aef12b8a x86
java  8u73     None 12c3e70c4348ba89e3817a5b48a41b26b1245550 amd64
java  8u74     None 8fa2c7f22b9176d0201d40dc21c29bc7002f5251 
java  jdk8u77  None 1560add14dde3e4c5bac020116f5bc06d49be567 
java  8u77     None c8a7641fb59e5a92118d6875c2598017852a89b1 x86
java  8u77     None bba6259c407aef6fb746140965d7285911c42ce1 amd64
java  jdk8u91  None 5374b68f6cca15345fd7d8de0b352cd37804068d 
java  8u91     None 917463bf8712a0f2ec17704fe7170c735088a915 x86
java  8u91     None 1b7710217149ff0981949c77aa8aa4cbc5597991 amd64
java  8u92     None b89aa89d66ea1783628f62487a137c993af7ca8b 
java  jdk8u101 None 2d2d56f5774cc2f15d9e54bebc9a868913e606b7 
java  8u101    None ae3ad283a4a175a3b5e1e143330ce194b7ebe560 x86
java  8u101    None cb8404bafad323694d7aa622f02d466073c61c2d amd64
java  8u102    None 3acf0fca1d5bf56f8a2ce577d055bfd0dd1773f9 
java  8u111    None 11d6a333a6d1b939a4d40082a4acab737071a7b8 x86
java  8u111    None 12e9492f2f2066f5b9187ed00995ede95491c445 amd64
java  jdk8u121 None e71fc3eb9f895eba5c2836b05d627884edd0157a 
java  8u121    None 22ae33babe447fb28789bce713a20cbee796a37c x86
java  8u121    None 8b22c68147ba96a8ac6e18360ff2739a1c6ca1db amd64
java  8u131    None 62762159368ea5fa7681913d2de3633c0d77ad2e x86
java  8u131    None a3a75ebdab5079aac1b3c2f2a4666296214f0417 amd64
java  8u141    None 74445e1c2c932f87ad90a55fb5da182f57dd637d x86
java  8u141    None 77cfba433ca2057e6aef6ac1f82f3a3679bf8533 amd64
java  8u144    None 49901a5961c2cdd9a46930d4008a8f8d0b1aad27 x86
java  8u144    None f1c74179507212cd853a87fa3b6a9ea764dea4ed amd64
java  8u151    None 94f6903ef5514405131298fc351af9467adf945d x86
java  8u151    None 57747ce996b5b2f1786601b04a0b0355fc82493a amd64
--------------------
java7
java7  jdk7     None 2546a78b6138466b3e23e25b5ca59f1c89c22d03 
java7  7        None 0faa00705651531c831380a6af83b564b995ecb0 
java7  jdk7u1   None ed434b8bc132a5bfda031428b26daf7b8331ecb9 
java7  7u1      None 26ec209d66c3b21ef3c7b6c1f3b9fa52466420ed x86
java7  7u1      None bd40f1dcd72326bb472cd131acb04d707566e706 amd64
java7  7u2      None a36ae80b80dd1c9c5c466b3eb2451cd649613cfb 
java7  jdk7u3   None fe9dc13c0a6424158dc0f13a6246a53973fb5369 
java7  7u3      None 61f48fa0875c85acc8fe1476a1297212f96ea827 x86
java7  7u3      None 0d74117467cd905f41fd807f7cdbaa671a150311 amd64
java7  7u4      None a2e927632b2106f5efefc906ed9070d8c0bf660f 
java7  jdk7u5   None 88c2fc5e5e61e7f709370c01abb138c65009307b 
java7  7u5      None 504d94c7cc1617b44af8d81de6fd83120b04dfa5 x86
java7  7u5      None ca01de8bf2290c9b891c0bf4aac4c099f66d80e7 amd64
java7  7u6      None 09f3a1d0fe7fabd4cfdc1c23d1ed16016d064d01 
java7  jdk7u7   None 58e4bdd12225379284542b161e49d8eaea4e00c2 
java7  7u7      None fad4496cd61a0ef1b42c27aeb405a3739ea0943f x86
java7  7u7      None 9af03460c416931bdee18c2dcebff5db50cb8cb3 amd64
java7  jdk7u9   None 11a256bd791033527580c6ac8700f3a72f7f4bcf 
java7  7u9      None 18c70915192bf5069543b8f95dd44f159ea6deec x86
java7  7u9      None 7ae6d07324439a203af612789110691f757b980e amd64
java7  jdk7u10  None f57bfa38a05433d902582fab9d08f530d7c7749b 
java7  7u10     None d159c752086d6134aacb2e15a10ccaf8ef39bca0 x86
java7  7u10     None 1c01773d0fd8e53af5fbf3cd2203ad6cf2545dbc amd64
java7  jdk7u11  None a482e48e151cff76dcc1479b9efc367da8fb66a7 
java7  7u11     None 682fb136563f08c20d37b25a28fce0883f893d8b x86
java7  7u11     None 41c3af2cf67c367066863a067ce831cf80586cdb amd64
java7  jdk7u13  None bd6848138385510b32897a5b04c94aa4cf2b4fca 
java7  7u13     None 72ad271c6c7e7d1893a9661aad2854a75e87cd5f x86
java7  7u13     None 0acc9b9d6a7f4ebd255c0cc720a6f452797c487f amd64
java7  jdk7u15  None f52453c6fd665b89629e639abdb41492eff9a9e3 
java7  7u15     None 5348714e363eb7df9ce5698cfcbb324e525cbd92 x86
java7  7u15     None 53345cc82bee2a8ddce8dea26992f371e25f37cd amd64
java7  jdk7u17  None 1f462dea65c74dd9fdf094d852e438a0e6a036bc 
java7  7u17     None 7b2cd00ec4c57396642afcc463e6d895772925a8 x86
java7  7u17     None eac554818507609480e8a890e232b3a8b0b2f55e amd64
java7  jdk7u21  None f677efa8309e99fe3a47ea09295b977af01f2142 
java7  7u21     None 620472dc1e7d015ed9a7700b846565a707946fcb x86
java7  7u21     None 9ec7523c5b8f5621ae21ab2fec12597ea029bb7f amd64
java7  jdk7u25  None 5eeb8869f9abcb8d575a7f75a6f85550edf680f5 
java7  7u25     None 08ce588fb3668e987a0fa93becf754e9c8027d51 x86
java7  7u25     None ad65e982d8ebf03bb2ddbb418aa26ab499daee41 amd64
java7  jdk7u40  None b611fb48bb5071b54ef45633cd796a27d5cd0ffd 
java7  7u40     None c0429dca47c0f22bbcd33492f39117245bab515d x86
java7  7u40     None 85c7db9a1c432a119c90d1d1b203ccaaedae3444 amd64
java7  jdk7u45  None cfd7e00fa0f6b3eef32832dd7487c6f56e7f55b8 
java7  7u45     None a2269c804418186c9b944746f26e225b3e77a571 x86
java7  7u45     None 155008d2cb8392befb4dcfec8afc5fd2c84173cc amd64
java7  jdk7u51  None 439435a1b40053761e3a555e97befb4573c303e5 
java7  7u51     None 72aa32f97a0ddd306d436ac3f13fabb841b94a76 x86
java7  7u51     None 0d3346f4c249d9443237205cc1c0dde1ef534874 amd64
java7  jdk7u55  None bb244a96e58724415380877230d2f6b466e9e581 
java7  7u55     None 96b937f49f07068313530db491b92e7e9afb80ba x86
java7  7u55     None 567c3bc32254b2235f0bc30e910323e2dd1e38aa amd64
java7  jdk7u60  None 8f9185b1fb80dee64e511e222c1a9742eff7837f 
java7  7u60     None 1672aed79505e52b6c39ee706d2f424910ad4493 x86
java7  7u60     None 29162a9087b41a0fb2a476ebc78ae5d2ae02495a amd64
java7  jdk7u65  None 9c52a8185b9931b8ae935adb63c8272cf6d9e9ba 
java7  7u65     None 0eb1db8fd71552ed48099881e2bde8bd41bbe53a x86
java7  7u65     None 8154af812e608bd0c8193c4d5e332a4133ed1aee amd64
java7  jdk7u67  None dff04608d4c045cdd66dffe726aed27b22939c9e 
java7  7u67     None cdcb564088e565b3ed56d9bc9d80448a4e3a9fc6 x86
java7  7u67     None 7d9413d367faa0b096ee72c2d5f1983bb7334e9e amd64
java7  jdk7u71  None 8ca5c5ad43148dfc0e5640db114e317f1bbd6a25 
java7  7u71     None b04ba06f787b596c57ede7e3c0250546d0635f73 x86
java7  7u71     None 714240cf53190bfccb0bb237323a2496300be946 amd64
java7  7u72     None 57f7dff98bdfbe064af159bbd1d8753cad714f68 
java7  jdk7u75  None 700e56c9b57f5349d4fe9ba28878973059dc68fa 
java7  7u75     None cd5f2222c6a9db6adfb385eaaeff8f95ea32446f x86
java7  7u75     None 488492de778fc47f67a33c65ea922124279c20d4 amd64
java7  7u76     None 0469ba6302aa3dc03e39075451aef1c60e5e4114 
java7  jdk7u79  None 319306c148c97f404c00e5562b11f5f4ea5fd6e5 
java7  7u79     None b062b03a04e0f3ce222282ca1760e4234d3c6f1f x86
java7  7u79     None 6e407b926eaf023e4248fdfffa810ded9d4ac7a3 amd64
java7 * 7u80     None aebbc0b02c16e7169b0577962fa91c613f8a7a45 
java7  8        None 09a05b1afad97ffa35a47d571752c3e804c200c7 
java7  jdk8u5   None 81660732a53e08651c633d99b0e6042cbbaf616d 
java7  8u5      None ca48401f6f71ad360b3c0882393e2c93c35f80de x86
java7  8u5      None ca656e8a722c068939665ad23760b8b072281594 amd64
java7  8u11     None 757103707b16e6a79ebd4d134613e483007a0c7a 
java7  8u20     None 30df3349f710e6b54adccadadc1e1f939ab2f6da 
java7  jdk8u25  None 79b4b68aea5ef6448c39c2ee3103722db6548ff0 
java7  8u25     None ff3d21c97e9ca71157f12221ccf0788a9775ec92 x86
java7  8u25     None 73024362b55d35f77562f203faba892c7540b68d amd64
java7  jdk8u31  None 5b8a1f8d11ecbcd46ed3389498ef67a4f699133b 
java7  8u31     None b8ef84ba6a68c35b5d7a5304b4c0304aa53858b8 x86
java7  8u31     None 00b5d23743d097d9b8f50bd14602bf4bae525b00 amd64
java7  jdk8u40  None ff9f4d62dffa0a81abbc0e5e151586301ddf4884 
java7  8u40     None c583ea81fe3cf6b06e2851f6805ec895226a0053 x86
java7  8u40     None 3034ee9474c8829cb9145f3ceadf4e4f8618b9f8 amd64
java7  jdk8u45  None 8e839fe0e30a56784566017f6acdb0fbe213c8bc 
java7  8u45     None 7fc89bd7f82a092d2aa15b753f1fa17e47b879aa x86
java7  8u45     None 4d71c0fccdad64149da2edbd89b8871c83ad5f7e amd64
java7  jdk8u51  None 0aaee8ff5f62fdcb3685d513be471c49824d7e04 
java7  8u51     None e0e42aaeedbb77a19809004a576496dcdcf99ed5 x86
java7  8u51     None 447fd1f59219282ec5d2f7a179ac12cc072171c3 amd64
java7  jdk8u60  None 47b36bc0fdc44029f82a50346fbb85b8f7803d7f 
java7  8u60     None bd486f62bc358b1180218480a1cbb0a42483af98 x86
java7  8u60     None 87976e29f58276685c63833ae42df7b2b5fe921c amd64
java7  jdk8u65  None 66bdacc1252f309f157fd0786d2e148dbb394629 
java7  8u65     None 5e0b4ef55faf1de9b4b85d769bfe0899481c5d79 x86
java7  8u65     None 85a8021af3299e5bc439a071e8b2cea6a137c6ad amd64
java7  jdk8u66  None 0013f600723a1a16aa97f7c3fbe1c27fd7674cbe 
java7  8u66     None b35523fe8891f4f29942482b0b9a205801294595 x86
java7  8u66     None b5a1871e28ab78aa0d48f0d61b3e03e98db50510 amd64
java7  jdk8u71  None c6726fb46cb40b42b4b545502ee87172b7d290f5 
java7  8u71     None 42db2fbd719a173f6d6d81bbb05f4033628c798c x86
java7  8u71     None 7875f835edf7383b221ca7a4f6b81072727f6eed amd64
java7  8u72     None d1b6e793c21f1bec935f647ec49a12bc54109ace 
java7  jdk8u73  None f56e21ece567f42fce5a38961bd81288dd2956c0 
java7  8u73     None 77551adf49d25bcbd3f9217190a87df8aef12b8a x86
java7  8u73     None 12c3e70c4348ba89e3817a5b48a41b26b1245550 amd64
java7  8u74     None 8fa2c7f22b9176d0201d40dc21c29bc7002f5251 
java7  jdk8u77  None 1560add14dde3e4c5bac020116f5bc06d49be567 
java7  8u77     None c8a7641fb59e5a92118d6875c2598017852a89b1 x86
java7  8u77     None bba6259c407aef6fb746140965d7285911c42ce1 amd64
java7  jdk8u91  None 5374b68f6cca15345fd7d8de0b352cd37804068d 
java7  8u91     None 917463bf8712a0f2ec17704fe7170c735088a915 x86
java7  8u91     None 1b7710217149ff0981949c77aa8aa4cbc5597991 amd64
java7  8u92     None b89aa89d66ea1783628f62487a137c993af7ca8b 
java7  jdk8u101 None 2d2d56f5774cc2f15d9e54bebc9a868913e606b7 
java7  8u101    None ae3ad283a4a175a3b5e1e143330ce194b7ebe560 x86
java7  8u101    None cb8404bafad323694d7aa622f02d466073c61c2d amd64
java7  8u102    None 3acf0fca1d5bf56f8a2ce577d055bfd0dd1773f9 
java7  8u111    None 11d6a333a6d1b939a4d40082a4acab737071a7b8 x86
java7  8u111    None 12e9492f2f2066f5b9187ed00995ede95491c445 amd64
java7  jdk8u121 None e71fc3eb9f895eba5c2836b05d627884edd0157a 
java7  8u121    None 22ae33babe447fb28789bce713a20cbee796a37c x86
java7  8u121    None 8b22c68147ba96a8ac6e18360ff2739a1c6ca1db amd64
java7  8u131    None 62762159368ea5fa7681913d2de3633c0d77ad2e x86
java7  8u131    None a3a75ebdab5079aac1b3c2f2a4666296214f0417 amd64
java7  8u141    None 74445e1c2c932f87ad90a55fb5da182f57dd637d x86
java7  8u141    None 77cfba433ca2057e6aef6ac1f82f3a3679bf8533 amd64
java7  8u144    None 49901a5961c2cdd9a46930d4008a8f8d0b1aad27 x86
java7  8u144    None f1c74179507212cd853a87fa3b6a9ea764dea4ed amd64
java7  8u151    None 94f6903ef5514405131298fc351af9467adf945d x86
java7  8u151    None 57747ce996b5b2f1786601b04a0b0355fc82493a amd64
--------------------
kb
kb  2729094 win7x64 e1a3ecc5030a51711f558f90dd1db52e24ce074b 
kb  2729094 win7x86 565e7f2a6562ace748c5b6165aa342a11c96aa98 
kb  2731771 win7x64 98dba6673cedbc2860c76b9686e895664d463347 
kb  2731771 win7x86 86675d2fd327b328793dc179727ce0ce5107a72e 
kb  2533623 win7x64 8a59ea3c7378895791e6cdca38cc2ad9e83bebff 
kb  2670838 win7x64 9f667ff60e80b64cbed2774681302baeaf0fc6a6 
kb  2670838 win7x86 984b8d122a688d917f81c04155225b3ef31f012e 
kb  2786081 win7x64 dc63b04c58d952d533c40b185a8b555b50d47905 
kb  2786081 win7x86 70122aca48659bfb8a06bed08cb7047c0c45c5f4 
kb  2639308 win7x64 67eedaf061e02d503028d970515d88d8fe95579d 
kb  2639308 win7x86 96e09ef9caf3907a32315839086b9f576bb46459 
kb  2834140 win7x64 3db9d9b3dc20515bf4b164821b721402e34ad9d6 
kb  2834140 win7x86 b57c05e9da2c66e1bb27868c92db177a1d62b2fb 
kb  2882822 win7x64 ec92821f6ee62ac9d2f74e847f87be0bf9cfcb31 
kb  2882822 win7x86 7fab5b9ca9b5c2395b505d1234ee889941bfb151 
kb  2888049 win7x64 fae6327b151ae04b56fac431e682145c14474c69 
kb  2888049 win7x86 65b4c7a5773fab177d20c8e49d773492e55e8d76 
kb  2819745 win7x64 5d40d059b9ea7f1d596f608a07cca49e4537dc15 
kb  2819745 win7x86 378bd9f96b8c898b86bb0c0b92f2c9c000748c5e 
kb  3109118 win7x64 ae0cac3e0571874dbc963dabbfa7d17d45db582c 
kb  3109118 win7x86 378bd9f96b8c898b86bb0c0b92f2c9c000748c5e 
--------------------
modified
--------------------
office
--------------------
office2007
--------------------
onemon
--------------------
optimizeos
--------------------
pillow
pillow * 2.9.0 None 1138f6db53b54943cbe7cf237c4df7e9255ca034 
pillow  3.4.2 None 46778e4c41cb721b035fb72b82e17bcaba94c077 
--------------------
ps1logging
--------------------
python
python  3.7.3  win7x64 bd95399506f362e7618d4f6b5a429ebf44714585 amd64
python  3.10.0 win10x64 3ee4e92a8ef94c70fb56859503fdc805d217d689 amd64
--------------------
removetooltips
removetooltips  None None 0de68031b1c1d17bf6851b13f2d083ee61b6b533 
--------------------
resolution
--------------------
silverlight
silverlight * 5.0.61118.0 None f0c3c1bce3802addca966783a33db1b668261fb5 x86
silverlight * 5.0.61118.0 None c98499e2a2f9ac0f8b70d301e3dee4d4cc4a5f86 amd64
silverlight  5.1.40620.0 None 45f07952e2e6cf8bd972a733aacb213871d086f1 x86
silverlight  5.1.40620.0 None 56ade2a82b7083383c9e4453af1da0301b48ac53 amd64
silverlight  5.1.50709.0 None 6e7c5e763ec6dba646adec4a0bcbd88059750658 x86
silverlight  5.1.50709.0 None 0222ec109d882a612d65c8ef8daa04af2f72f8fa amd64
silverlight  5.1.50905.0 None 97b56d4e390241ae1baabe65d41e4080270bcb1b x86
silverlight  5.1.50905.0 None 16712886955bab475549184015d425e3091a6357 amd64
silverlight  5.1.50906.0 None 7a811b061f742479d2e25ce5ac1a9908f5745bf1 x86
silverlight  5.1.50906.0 None d10a077bf0043a846f2f2a75962c2e068a060f10 amd64
--------------------
sysmon
sysmon  6.0.2 None ce9edbea1937d593bf6cba4d9ca57d66f1680fdf amd64
sysmon  6.0.2 None b97d720eca991bd96d6a8d60ea93ee163e09178d x86
sysmon * 8.0.0 None 173014bedc7d852a4cee961440ffaf06fa716353 amd64
sysmon * 8.0.0 None 8cc70223e7f667387d9792a5183129734d3b5501 x86
--------------------
threemonpatch
threemonpatch  None None a8f8ed626b9fc9f66938ac034db4e8750664a6ac amd64
--------------------
vcredist
vcredist  2005    None 47fba37de95fa0e2328cf2e5c8ebb954c4b7b93c x86
vcredist  2005    None 90a3d2a139c1a106bfccd98cbbd7c2c1d79f5ebe amd64
vcredist * 2005sp1 None 7dfa98be78249921dd0eedb9a3dd809e7d215c8d x86
vcredist * 2005sp1 None 756f2c773d4733e3955bf7d8f1e959a7f5634b1a amd64
vcredist  2008    None 56719288ab6514c07ac2088119d8a87056eeb94a x86
vcredist  2008    None 5580072a056fdd50cdf93d470239538636f8f3a9 amd64
vcredist  2008sp1 None 6939100e397cef26ec22e95e53fcd9fc979b7bc9 x86
vcredist  2008sp1 None 13674c43652b941dafd2049989afce63cb7c517b amd64
vcredist  2010    None 372d9c1670343d3fb252209ba210d4dc4d67d358 x86
vcredist  2010    None b330b760a8f16d5a31c2dc815627f5eb40861008 amd64
vcredist  2010sp1 None b84b83a8a6741a17bfb5f3578b983c1de512589d x86
vcredist  2010sp1 None 027d0c2749ec5eb21b031f46aee14c905206f482 amd64
vcredist  2012    None 407951838ef622bbfd2e359f0019453dc9a124ed x86
vcredist  2012    None 60727ca083e3625a76c3edbba22b40d8a35ffd6b amd64
vcredist  2012u1  None d292afddbae41acb2a1dfe647e15336ad7375c6f x86
vcredist  2012u1  None abe47e4996cf0409a794c1844f1fa8404032edb2 amd64
vcredist  2012u3  None 7d6f654c16f9ce534bb2c4b1669d7dc039c433c9 x86
vcredist  2012u3  None c4ac45564e801e1bfd87936cac8a76c5754cdbd4 amd64
vcredist  2012u4  None 96b377a27ac5445328cbaae210fc4f0aaa750d3f x86
vcredist  2012u4  None 1a5d93dddbc431ab27b1da711cd3370891542797 amd64
vcredist  2013    None df7f0a73bfa077e483e51bfb97f5e2eceedfb6a3 x86
vcredist  2013    None 8bf41ba9eef02d30635a10433817dbb6886da5a2 amd64
vcredist  2013u4  None a2889d057d63da00f2f8ab9c4ed1e127bdf5db68 x86
vcredist  2013u4  None c990b86c2f8064c53f1de8c0bffe2d1c463aaa88 amd64
vcredist  2013u5  None 2a07a32330d5131665378836d542478d3e7bd137 x86
vcredist  2013u5  None 261c2e77d288a513a9eb7849cf5afca6167d4fa2 amd64
vcredist  2015    None bfb74e498c44d3a103ca3aa2831763fb417134d1 x86
vcredist  2015    None 3155cb0f146b927fcc30647c1a904cd162548c8c amd64
vcredist  2015u1  None 89f20df555625e1796a60bba0fbd2f6bbc627370 x86
vcredist  2015u1  None cd2fce1bf61637b2536b66ee52a9662473bbdc82 amd64
vcredist  2015u2  None e99e5b17b0ad882833bbdc8cf798dc56f9947a5e x86
vcredist  2015u2  None ff15c4f5da3c54f88676e6b44f3314b173835c28 amd64
vcredist  2015u3  None 72211bd2e7dfc91ea7c8fac549c49c0543ba791b x86
vcredist  2015u3  None 10b1683ea3ff5f36f225769244bf7e7813d54ad0 amd64
vcredist  2019    None de385d69864413400250f2f3fe9f4aec78eb997b amd64
--------------------
wallpaper
--------------------
wic
wic  None None 53c18652ac2f8a51303deb48a1b7abbdb1db427f x86
wic  None None da12927da6eb931a39e479d55c8b0321e8367f5e amd64
--------------------
win7sp
win7sp * sp1 win7x64 74865ef2562006e51d7f9333b4a8d45b7a749dab 
win7sp * sp1 win7x86 c3516bc5c9e69fee6d9ac4f981f5b95977a8a2fa 
--------------------
winddk
--------------------
winrar
winrar * 5.31 None 48add5a966ed940c7d88456caf7a5f5c2a6c27a7 amd64
winrar * 5.31 None e19805a1738975aeec19a25a4e461d52eaf9b231 x86
winrar  5.40 None 22ac3a032f37ce5dabd0673f401f3d0307f21b74 amd64
winrar  5.40 None 211a19ca4ec3c7562c9844fe6c42e66a521b8bd4 x86
--------------------
zer0m0n
--------------------
```

</details>

---
