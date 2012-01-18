#!/usr/bin/perl
# vi: set ts=8 sw=2 et:

use strict;
use warnings;
use CGI;
#use CGI::Carp qw(fatalsToBrowser);
use DBI;
use HTTP::Request::Common qw(POST);
use HTML::Template;
use LWP::UserAgent;
use Mail::Mailer;
use XML::Simple;
use Data::Dumper;
use Business::OnlinePayment;
use Business::CreditCard;
use Geo::IP::PurePerl;
use Locale::gettext;
use POSIX;     # Neede_DEd for setlocale()
require '/home/OrderSystem/public_html/SecureProcess/includes/pnpremote.pm';
require '/etc/ProcessFiles/neildb.pm';
require '/etc/ProcessFiles/securedb.pm';
require '/etc/ProcessFiles/secure.pm';
require '/etc/ProcessFiles/camdb.pm';
$ENV{'PERL_LWP_SSL_VERIFY_HOSTNAME'} = 0;

my %cc_name = (Visa => 'VISA card', Mastercard => 'MasterCard', Discover => 'Discover card', 'American Express' => 'American Express card');




my $query = new CGI ;
my $returntime = '6:30AM EST';

#print $query->header(), "<html><head><title>Short Server Maintenance</title></head><body><h1>Server maintenance in progress - we'll be back in a moment <br></h1></body></html>";
#exit;

# for video:
# storeid=152  id=1842:DVD  CheckOut=Order%20Videos
# storeid=152  id=1841:DVD  id=1842:DVD  id=945:DVD  id=946:DVD - PAL CheckOut=Order%20Videos
# for clips:
# storeid=1587  id=38522  id=38639  CheckOut=1  CheckOut=
# storeid=1587  id=38522  id=38639  CheckOut=1  CheckOut=

my $q = CGI->new();
my $ua = LWP::UserAgent->new(timeout => 60);
my $mailer = new Mail::Mailer->new( 'smtp', Server => 'mailout2.intermarkproductions.com');
my @uniqids;

#encryption strings.
my $ccEncryptString = $ClipSecure::cc . '448662ys7';
my $nameEncryptString = $ClipSecure::name . '75nsh';
my $emailEncryptString = $ClipSecure::email . '22kk6u6';

my $GetRidOfNameOnceError = $ClipSecure::cc;
$GetRidOfNameOnceError = $ClipSecure::name;
$GetRidOfNameOnceError = $ClipSecure::email;
$GetRidOfNameOnceError = $camdb::database;
$GetRidOfNameOnceError = $camdb::dbadmin;
$GetRidOfNameOnceError = $camdb::dbpasswd;
$GetRidOfNameOnceError = "";

#RADIO radio Radio contest
my $RadioHTML = '';
my $RadioID = '';
if ($q->param('RadioID')) {
  my $RadioID = $q->param('RadioID');
  if ($RadioID eq '100'){$RadioHTML = "\n\n Radio Listeners go to http://www.clipcash.com and click the Get Card button.  Follow the instructions and fill out your information. Upon completion you will receive a clipcash ID with a \$6 credit that can be redeemed at http://www.clips4sale.com.";}
}
  my $service = 'PClipOrder';
  $service = 'P Video Order' if $q->param('CheckOut') eq 'Order Videos';
  $service = 'P Image Order' if $q->param('CheckOut') eq 'Order Pixxx';
  $service = 'P Cam Order' if $q->param('CheckOut') eq 'Cam_Order';

# are we removing an item? (there can be only one...)
my ($remove) = map { s/^Remove-//; $_ } grep { /^Remove-/ } $q->param;
$remove = 0 if ! defined $remove;

my @id = grep { $_ ne $remove } $q->param('id');
my $remote_host = $ENV{'REMOTE_HOST'};
my $remote_addr = $ENV{'REMOTE_ADDR'};
my $http_user_agent = $ENV{'HTTP_USER_AGENT'};
my $storeid = $q->param('storeid');
if ($storeid =~ /[aA-zZ]/){ 
print $query->header(), "<html><body>Invalid Data</body></html>";
exit;
}
#$storeid =~ s/[^0-9]//;
my $pay_method = $q->param('PayMethod') || '';
my $credit_card = $q->param('Credit_Card_Number');
my $credit_card_name = $q->param('CardName');
my $OrderType = $q->param('CheckOut');
my $ordertypenew = $q->param('CheckOut');
my $eurobill = $q->param('Ebill') || 0;

#if ($remote_addr eq "65.101.102.77"){
# open SLOWTEST, ">>/home/OrderSystem/public_html/SecureProcess/test.log";
# print SLOWTEST $datetime;
#}
if ($OrderType eq 'Cam_Order00') { 
print $query->header(), "<html><head><title>Short Server Maintenance</title></head><body><h1>Server maintenance in progress - we'll be back in a moment <br></h1></body></html>";
exit;
}

my $transID  = $q->param('TransID');
if ($transID =~ /[^0-9]/){ 
print $query->header(), "<html><body>Invalid Data</body></html>";
exit;
}
my $camVerify;
my $camUserName;
my $camProductName;
my $camPrice;
my $camType;
my $csth;
my $camDB = DBI->connect_cached($camdb::database, $camdb::dbadmin, $camdb::dbpasswd) if ($OrderType eq 'Cam_Order');
if ($OrderType eq 'Cam_Order') {
  if ($transID ne ''){
      #put the sql to get the storeID and stuff here.
      $csth = $camDB->prepare("SELECT verify, s.domain, p.fkid, p.product_name, p.price, p.type FROM payments p left join stores s on s.id=p.fkid WHERE p.id= $transID");
          if (!defined($csth) || !$csth->execute()) {print "\n(Get data from the Cam Site TablesSTH: " . $camDB->errstr . "<br>\n"; die;}
            my $row_ref = $csth->fetchrow_hashref();
          $storeid = $row_ref->{'fkid'};
          ## !!!!!!!!!!!!! REMOVE ME !!!!!!!!!!!!!
          #$storeid = 18;
          ## !!!!!!!!!!!!! REMOVE ME !!!!!!!!!!!!!
          $camVerify = $row_ref->{'verify'};
          $camUserName = $row_ref->{'domain'};
          $camProductName = $row_ref->{'product_name'};
          $camPrice = $row_ref->{'price'};
          $camType = $row_ref->{'type'};
      @id = 1;
  }
}



my $analytics = 'UA-3043756-1';
if ($q->virtual_host() =~ /.*?prepa.*/gi) {
} elsif ($q->virtual_host() =~ /.*?(pixxx|images).*/gi) {
        $analytics = 'UA-3043756-2';
} elsif ($q->virtual_host() =~ /.*?(videos).*/gi) {
        $analytics = 'UA-3043756-3';
}

  
my $vidformat = 'DVD';
my $optin = $q->param('maillist');
$credit_card =~ s/\D//g if defined $credit_card;
my $log_in = '';
my $title = '';
my ($maxmind_ccfs_info,$proxyScore,$spamScore,$score, $anonymousProxy, $MaxCountry, $MaxDistance, $MaxHighRisk, $MaxIPRegion, $MaxID, $MaxISP, $MaxORG, $MaxCity, $MaxState, $MaxSpamScore) = ('','','','','','','','','','','','','','','');
my $cc_addl_reqd = 0;
$cc_addl_reqd = 1 if $q->param('Addl_Reqd');

my $gizmo_g;
my $the_domain;
my $gizmo_sub = '';
if ($q->virtual_host() =~ /.*?prepa.*/gi) {
  $gizmo_g = 1;
  $the_domain = "PrePaidClips.com";
  $gizmo_sub = "PrePaid";
} elsif ($q->virtual_host() =~ /.*?(pixxx|images).*/gi) {
  $gizmo_g = 0;
  $the_domain = "Images4sale.com";
  $gizmo_sub = "Pixxx";
} else {
  $gizmo_g = 0;
  $the_domain = "Clips4Sale.com";
}
if ($q->param('CheckOut') eq 'Order Videos') {
  $gizmo_g = 0;
  $the_domain = "Videos4Sale.com";
}
if ($q->param('CheckOut') eq 'Order Pixxx') {
  $gizmo_g = 0;
  $the_domain = "Images4Sale.com";
}

# get country name from IP
my $remote_country;
{
  my $gi = Geo::IP::PurePerl->new(GEOIP_STANDARD);
  my $cn = $gi->country_name_by_addr($remote_addr);
  $remote_country = defined $cn ? $cn : "unknown";
}

my $dbhS;
my $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
if (!defined($dbh)) {print $q->header() . "DBI: " . $DBI::errstr; die;}

my ($cc, $descriptor, $hold_percent, $umkey, $ePNAccount, $goEMerch, $goEPasswd, $authNname, $authNpasswd, $linkPconfig, $linkPkeyfile, $cpstnID, $cpstnPW, $error, $paygeaID, $paygeaPW, $paygeaAccount, $plugandpay, $paygateid, $paygatepw, $firePayNum, $fireID, $firePWD);
# Is this store configured for a gateway?

## PUT CAMBILL STUFF HERE>  IF Cam then do one way, if not then the other.##


my $sth;
if ($OrderType eq 'Cam_Order'){
        my $ccCO;
        my $sth = $dbh->prepare("select cc from ProducerMerchant where ProducerID = $storeid");
  $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
  if (!defined($sth) || !$sth->execute()) {die $q->header() . "\n\n(select prodmerch) STH: " . ":: " . $dbh->errstr . "<br>\n";}
  $sth->bind_columns(\$ccCO);
  $sth->fetch();


        if (defined($ccCO)) { 
          my $sth = $dbh->prepare("
            select
            m.cc, m.descriptor, m.hold_percent,
            m.umkey,
            m.ePNAccount,
            m.goEMerch, m.goEPasswd,
            m.authNname, m.authNpasswd,
            m.linkPconfig, m.linkPkeyfile,
            m.capstoneID, m.capstonePasswd,
            m.paygeaID, m.paygeaPW, m.paygeaAccount,
            m.plugandpay, m.paygateid, m.paygatepw, m.firePayNum, m.fireID, m.firePWD
            from Merchant_Account m
            where m.cc = 905
            ");
          $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
          if (!defined($sth) || !$sth->execute()) {die $q->header() . "\n\n(select prodmerch) STH: " . ":: " . $dbh->errstr . "<br>\n";}
          $sth->bind_columns(\$cc, \$descriptor, \$hold_percent, \$umkey, \$ePNAccount, \$goEMerch, \$goEPasswd, \$authNname, \$authNpasswd, \$linkPconfig, \$linkPkeyfile, \$cpstnID, \$cpstnPW, \$paygeaID, \$paygeaPW, \$paygeaAccount, \$plugandpay, \$paygateid, \$paygatepw, \$firePayNum, \$fireID, \$firePWD);
          $sth->fetch();
        }

}elsif ($eurobill == 1) {

  my $sth = $dbh->prepare("
          select
          m.cc, m.descriptor, m.hold_percent,
          m.umkey,
          m.ePNAccount,
          m.goEMerch, m.goEPasswd,
          m.authNname, m.authNpasswd,
          m.linkPconfig, m.linkPkeyfile,
          m.capstoneID, m.capstonePasswd,
          m.paygeaID, m.paygeaPW, m.paygeaAccount,
          m.plugandpay, m.paygateid, m.paygatepw, m.firePayNum, m.fireID, m.firePWD
          from Merchant_Account m
          where m.cc = 921
          ");
        $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
        if (!defined($sth) || !$sth->execute()) {die $q->header() . "\n\n(select prodmerch) STH: " . ":: " . $dbh->errstr . "<br>\n";}
        $sth->bind_columns(\$cc, \$descriptor, \$hold_percent, \$umkey, \$ePNAccount, \$goEMerch, \$goEPasswd, \$authNname, \$authNpasswd, \$linkPconfig, \$linkPkeyfile, \$cpstnID, \$cpstnPW, \$paygeaID, \$paygeaPW, \$paygeaAccount, \$plugandpay, \$paygateid, \$paygatepw, \$firePayNum, \$fireID, \$firePWD);
        $sth->fetch();
}

else{

my $sth = $dbh->prepare("
  select
  m.cc, m.descriptor, m.hold_percent,
  m.umkey,
  m.ePNAccount,
  m.goEMerch, m.goEPasswd,
  m.authNname, m.authNpasswd,
  m.linkPconfig, m.linkPkeyfile,
  m.capstoneID, m.capstonePasswd,
  m.paygeaID, m.paygeaPW, m.paygeaAccount,
  m.plugandpay, m.paygateid, m.paygatepw, m.firePayNum, m.fireID, m.firePWD
  from Merchant_Account m
  left join ProducerMerchant p on m.cc = p.cc
  where p.ProducerID = $storeid
  ");
$dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
if (!defined($sth) || !$sth->execute()) {die $q->header() . "\n\n(select prodmerch) STH: " . ":: " . $dbh->errstr . "<br>\n";}
$sth->bind_columns(\$cc, \$descriptor, \$hold_percent, \$umkey, \$ePNAccount, \$goEMerch, \$goEPasswd, \$authNname, \$authNpasswd, \$linkPconfig, \$linkPkeyfile, \$cpstnID, \$cpstnPW, \$paygeaID, \$paygeaPW, \$paygeaAccount, \$plugandpay, \$paygateid, \$paygatepw, \$firePayNum, \$fireID, \$firePWD);
$sth->fetch();


#CHAGEN 06-06-2011 videos4sale and images4sale re-route orders

#If this is a video or image check something.
if ($q->param('CheckOut') eq 'Order Pixxx' || $q->param('CheckOut') eq 'Order Videos')
  {
    if ($cc == 5 || $cc == 24 || $cc == 30 || $cc == 909 || $cc == 912 || $cc == 913 || $cc == 914) {
        
        my %ccroutelist = (5 => 911,
               24 => 910,
               30 => 910,
            909 => 910,
            912 => 910,
            913 => 910,
            914 => 910
            );
      my $sth = $dbh->prepare("
        select
        m.cc, m.descriptor, m.hold_percent,
        m.umkey,
        m.ePNAccount,
        m.goEMerch, m.goEPasswd,
        m.authNname, m.authNpasswd,
        m.linkPconfig, m.linkPkeyfile,
        m.capstoneID, m.capstonePasswd,
        m.paygeaID, m.paygeaPW, m.paygeaAccount,
        m.plugandpay, m.paygateid, m.paygatepw, m.firePayNum, m.fireID, m.firePWD
        from Merchant_Account m
        where m.cc = ?");
      $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
      if (!defined($sth) || !$sth->execute($ccroutelist{$cc})) {die $q->header() . "\n\n(select prodmerchIV) STH: " . ":: " . $dbh->errstr . "<br>\n";}
      $sth->bind_columns(\$cc, \$descriptor, \$hold_percent, \$umkey, \$ePNAccount, \$goEMerch, \$goEPasswd, \$authNname, \$authNpasswd, \$linkPconfig, \$linkPkeyfile, \$cpstnID, \$cpstnPW, \$paygeaID, \$paygeaPW, \$paygeaAccount, \$plugandpay, \$paygateid, \$paygatepw, \$firePayNum, \$fireID, \$firePWD);
      $sth->fetch();
    }
  }




#Redirect visa
if ($credit_card){
if ($credit_card =~ /^4/ and $cc == 3){
# my $sth = $dbh->prepare("
#  select
#  m.cc, m.descriptor, m.hold_percent,
#  m.umkey,
#  m.ePNAccount,
# m.goEMerch, m.goEPasswd,
#  m.authNname, m.authNpasswd,
#  m.linkPconfig, m.linkPkeyfile,
#  m.capstoneID, m.capstonePasswd
#  from Merchant_Account m
#  left join ProducerMerchant p on m.cc = p.cc
#  where p.cc = 31 or p.cc = 33 or p.cc = 34
#   order by Rand() limit 1
#");
 my $sth = $dbh->prepare("
      select
        m.cc, m.descriptor, m.hold_percent,
        m.umkey,
        m.ePNAccount,
        m.goEMerch, m.goEPasswd,
        m.authNname, m.authNpasswd,
        m.linkPconfig, m.linkPkeyfile,
        m.capstoneID, m.capstonePasswd,
        m.paygeaID, m.paygeaPW, m.paygeaAccount, m.plugandpay
      from Merchant_Account m
      left join ProducerMerchant p on m.cc = p.cc
      where p.cc = (
           select z.cc from (
                select  t.cc
                 , sum(t.TotalAmount) as totamt
                from    Transactions t
                where
                   (t.cc = 31 or t.cc = 33 or t.cc = 34 or t.cc = 40 or t.cc = 25 or t.cc = 29)
                   and t.DateOfTransaction > curdate()
                   group by t.cc
                   order by totamt
                   limit 1
                ) z
            )
            limit 1
   ");

   $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
 if (!defined($sth) || !$sth->execute()) {die $q->header() . "\n\n(select prodmerch) STH: " . $dbh->errstr . "<br>\n";}
 $sth->bind_columns(\$cc, \$descriptor, \$hold_percent, \$umkey, \$ePNAccount, \$goEMerch, \$goEPasswd, \$authNname, \$authNpasswd, \$linkPconfig, \$linkPkeyfile, \$cpstnID, \$cpstnPW, \$paygeaID, \$paygeaPW, \$paygeaAccount, \$plugandpay, );
  $sth->fetch();
   }}
#                                                                                             

#Redirect Israel for Paygea acounts
if ($credit_card ne '' && $remote_country eq "Israel" && $cc < 20){
   my $sth = $dbh->prepare("
      select
        m.cc, m.descriptor, m.hold_percent,
        m.umkey,
        m.ePNAccount,
        m.goEMerch, m.goEPasswd,
        m.authNname, m.authNpasswd,
        m.linkPconfig, m.linkPkeyfile,
        m.capstoneID, m.capstonePasswd,
        m.paygeaID, m.paygeaPW, m.paygeaAccount, m.plugandpay
        from Merchant_Account m
        where cc = 24
    ");
   $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
   if (!defined($sth) || !$sth->execute()) {die $q->header() . "\n\n(select prodmerch) STH: " . $dbh->errstr . "<br>\n";}
   $sth->bind_columns(\$cc, \$descriptor, \$hold_percent, \$umkey, \$ePNAccount, \$goEMerch, \$goEPasswd, \$authNname, \$authNpasswd, \$linkPconfig, \$linkPkeyfile, \$cpstnID, \$cpstnPW, \$paygeaID, \$paygeaPW, \$paygeaAccount, \$plugandpay);
   $sth->fetch();
 } 


#Redirect Mastercard  DEPRECIATED
if ($credit_card){
if ($credit_card =~ /^5/ and $cc == 3){
my $sth = $dbh->prepare("
      select
        m.cc, m.descriptor, m.hold_percent,
        m.umkey,
        m.ePNAccount,
        m.goEMerch, m.goEPasswd,
        m.authNname, m.authNpasswd,
        m.linkPconfig, m.linkPkeyfile,
        m.capstoneID, m.capstonePasswd,
        m.paygeaID, m.paygeaPW, m.paygeaAccount, m.plugandpay
        from Merchant_Account m
        left join ProducerMerchant p on m.cc = p.cc
      where p.cc = (
            select z.cc from (
                select  t.cc
                  , sum(t.TotalAmount) as totamt
                from    Transactions t
                where
                  (t.cc = 31 or t.cc = 33 or t.cc = 34 or t.cc = 40 or t.cc = 25 or t.cc = 29)
                  and t.DateOfTransaction > curdate()
                group by t.cc
                order by totamt
                limit 1
              ) z
           )
           limit 1
    ");
   $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
   if (!defined($sth) || !$sth->execute()) {die $q->header() . "\n\n(select prodmerch) STH: " . $dbh->errstr . "<br>\n";}
   $sth->bind_columns(\$cc, \$descriptor, \$hold_percent, \$umkey, \$ePNAccount, \$goEMerch, \$goEPasswd, \$authNname, \$authNpasswd, \$linkPconfig, \$linkPkeyfile, \$cpstnID, \$cpstnPW, \$paygeaID, \$paygeaPW, \$paygeaAccount, \$plugandpay);
   $sth->fetch();
 }} 

#Redirect Amex
if ($credit_card ne ''){
if ($credit_card =~ /^37/ ){
    $paygeaID = '';
    my $sth = $dbh->prepare("
        select
        m.cc, m.descriptor, m.hold_percent,
        m.umkey,
        m.ePNAccount,
        m.goEMerch, m.goEPasswd,
        m.authNname, m.authNpasswd,
        m.linkPconfig, m.linkPkeyfile,
        m.capstoneID, m.capstonePasswd,
        m.paygeaID, m.paygeaPW, m.paygeaAccount, m.plugandpay
        from Merchant_Account m
        left join ProducerMerchant p on m.cc = p.cc
        where p.cc = 30
        order by Rand() limit 1
        ");
     $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
     if (!defined($sth) || !$sth->execute()) {die $q->header() . "\n\n(select prodmerch) STH: " . $dbh->errstr . "<br>\n";}
     $sth->bind_columns(\$cc, \$descriptor, \$hold_percent, \$umkey, \$ePNAccount, \$goEMerch, \$goEPasswd, \$authNname, \$authNpasswd, \$linkPconfig, \$linkPkeyfile, \$cpstnID, \$cpstnPW, \$paygeaID, \$paygeaPW, \$paygeaAccount, \$plugandpay);
      $sth->fetch();
     }}

#Redirect Discover
if ($credit_card ne ''){
if ($credit_card =~ /^60/){
   $paygeaID = '';
    my $sth = $dbh->prepare("
       select
       m.cc, m.descriptor, m.hold_percent,
       m.umkey,
       m.ePNAccount,
       m.goEMerch, m.goEPasswd,
       m.authNname, m.authNpasswd,
       m.linkPconfig, m.linkPkeyfile,
       m.capstoneID, m.capstonePasswd,
       m.paygeaID, m.paygeaPW, m.paygeaAccount, m.plugandpay
       from Merchant_Account m
       left join ProducerMerchant p on m.cc = p.cc
       where p.cc = 24 or p.cc = 30
       order by Rand() limit 1
       ");
    $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
    if (!defined($sth) || !$sth->execute()) {die $q->header() . "\n\n(select prodmerch) STH: " . $dbh->errstr . "<br>\n";}
    $sth->bind_columns(\$cc, \$descriptor, \$hold_percent, \$umkey, \$ePNAccount, \$goEMerch, \$goEPasswd, \$authNname, \$authNpasswd, \$linkPconfig, \$linkPkeyfile, \$cpstnID, \$cpstnPW, \$paygeaID, \$paygeaPW, \$paygeaAccount, \$plugandpay);
    $sth->fetch();
 }}

}
 
$descriptor = 'Gizmo Card Account' if $pay_method eq 'GizmoCard';
$descriptor = 'Clip Cash Card' if $pay_method eq 'ClipCash';
my @chars = ("A" .. "Z", "a" .. "z", 0 .. 9);
my $rande = join('', @chars[map{rand @chars}(1 .. 20)]);

my %states;
$dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
$sth = $dbh->prepare("select state_id, state from states");
if (!defined($sth) || !$sth->execute()) {die $q->header() . '(select states) STH:' . $dbh->errstr . "<br>\n";}
while (my $row_ref = $sth->fetchrow_hashref()) {
  $states{$row_ref->{'state_id'}} = $row_ref->{'state'};
}
$sth->finish();

my %countries;
my %countries_rev;
my %countries_num;
$dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
$sth = $dbh->prepare("select country_id, country, country_num_id from countries where active = 1");
if (!defined($sth) || !$sth->execute()) {die $q->header() . '(select countries) STH:' . $dbh->errstr . "<br>\n";}
while (my $row_ref = $sth->fetchrow_hashref()) {
  $countries{$row_ref->{'country'}} = $row_ref->{'country_id'};
  $countries_rev{$row_ref->{'country_id'}} = $row_ref->{'country'};
  $countries_num{$row_ref->{'country_id'}} = $row_ref->{'country_num_id'};
}
$sth->finish();


if (defined $q->param('Session')) {
  $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
  $sth = $dbh->prepare("select * from Session where ID = '" . esc($q->param('Session')) . "' and Store = '3'");
  if (!defined($sth) || !$sth->execute()) {print "\n(select session) STH: " . $dbh->errstr; die;}
  if ($sth->rows) {print $q->redirect(-uri => 'http://www.' . $the_domain); exit;}
 $sth->finish();
  
}

my $customer_id = $q->cookie('CustomerID');
my $referrer = $q->param('referrer');
my $CampaignCode = $q->param('CampaignCode');
my $domain = $q->url(-base => 1);
if (!$customer_id) {
  $domain =~ s/^http:\/\///;
  $domain =~ s/^.*(\.[^.]+\.[^.]+)$/$1/;
  $domain = '.' . $domain if substr($domain,0,1) ne '.';
  $customer_id = time . $ENV{'REMOTE_ADDR'};
  $customer_id =~ s/\D+//g;
  my $cookie = $q->cookie(
    -name    => 'CustomerID',
    -value   => $customer_id,
    -expires => '+10y',
    -domain  => $domain,
    -secure  => 1,
  );
  print $q->header(-cookie => $cookie);
} elsif ($OrderType eq 'Cam_Order' and ($q->param('Pay_Order') && $q->param('TransID') ne '')){
} else {
  print $q->header();
  #print "<br><Br>Referrer = " . $referrer . "<br><Br>"; 
}

$sth = $dbh->prepare("select 1 as PF from (select 1) a where (select min(DateOfTransaction) from Transactions where CustomerID = '$customer_id') < NOW() - interval 4 month");
if (!defined($sth) || !$sth->execute()) {die $q->header() . '(select OldCustomer) STH:' . $dbh->errstr . "<br>\n";}
my $row_ref = $sth->fetchrow_hashref();
my $OldCustomer = $row_ref->{'PF'};
$sth->finish();
    
my %vidhash = ();

my $CCtype = 'clip';
for ($OrderType) {
    /Cam_Order/i && do{
    $CCtype = 'cam';
  };
  /Order Videos/i && do{
    $CCtype = 'video';
    $sth = $dbh->prepare("select * from VideoFormats");
    if (!defined($sth) || !$sth->execute()) {die $q->header() . '(select VidFormats) STH:' . $dbh->errstr . "<br>\n";}
    while($row_ref = $sth->fetchrow_hashref()){
      $vidhash{$row_ref->{'FormatValue'}} = $row_ref->{'FormatID'};
    }
    $sth->finish();
    
  };
  /Order Pixxx/i && do{
    $CCtype = 'image';
  };
};
my $returnval;
my $CCreturnval;
foreach my $id (@id) {
  if ($id ne '') {$returnval .= "&id[]=$id";
    if ($CCtype eq 'video') {
      my ($idL,$idR) = split(/:/,$id);
      $id = $idL . ":" . $vidhash{$idR};
    } 
    $CCreturnval .= "&id[$CCtype][]=$id";
  }
  
}
$returnval = reverse($returnval);
chop($returnval);
$returnval = reverse($returnval);

$CCreturnval = reverse($CCreturnval);
chop($CCreturnval);
$CCreturnval = reverse($CCreturnval);

my $DEBurl = "https://secure.sun-tropic.com/deb/orderDIRECTebanking.php?$returnval";
my $CCurl =  "https://secure.sun-tropic.com/clipcash/order.php?$CCreturnval";

if ($OrderType eq 'Cam_Order') {

  $DEBurl = "";
  #$DEBurl = "https://secure.sun-tropic.com/deb/orderDIRECTebanking.php?$transID";
  $CCurl =  "https://secure.sun-tropic.com/clipcash/order.php?id[cam][]=$transID";
}
if ($OrderType eq 'Order Videos' || $OrderType eq 'Order Pixxx') {
  $DEBurl = "";
}

my $template = HTML::Template->new(filename => "securebill.html");
TranslateHeadings();
$template->param(analytics => $analytics);
$template->param(eurobill => $eurobill);
my $maxdomain = $domain;
$maxdomain =~ s/https:\/\///;
$template->param(maxdomain => $maxdomain);

# Link to SofoPay or Direct E Banking  CHAGEN 02/25/2011
#$template->param(directebanking => $DEBurl);
#RADIO radio Radio contest
$template->param(RadioID => $RadioID);

if (defined $authNname) {
  $template->param(authNet => 1);
}

if (defined $q->param('CheckOut')) {
  my $x = $q->param('CheckOut');
  $template->param(CheckOut => $x);
}
my $IsClipOrder = 0;
my $site_table;
my %ctry_ship;
if ($q->param('CheckOut') eq 'Order Videos') {
  $site_table = 'ProducerVideoSite';
  $template->param(order_clips => 0);
  $template->param(order_pixxx => 0);
  $template->param(order_videos => 1);
  $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
  $sth = $dbh->prepare("select * from ProducerVideoSiteShipping where SiteID = ?");
  if (!defined($sth) || !$sth->execute($q->param('storeid'))) {print "\n(select site info) STH: " . $dbh->errstr . "<br>\n"; die;}
  my ($ctry_array, $ship_array);
  while (my $row_ref = $sth->fetchrow_hashref()) {
    $ctry_array .= ',' if $ctry_array;
    $ship_array .= ',' if $ship_array;
    $ctry_array .= "'$row_ref->{'country_id'}'";
    $ship_array .= $row_ref->{'shipping'};
    $ctry_ship{$row_ref->{'country_id'}} = $row_ref->{'shipping'};
  }
  $template->param(ctry_array => $ctry_array);
  $template->param(ship_array => $ship_array);
} elsif ($q->param('CheckOut') eq 'Order Pixxx') {
  $site_table = 'ProducerImageSite';
  $template->param(order_clips => 0);
  $template->param(order_pixxx => 1);
  $template->param(order_videos => 0);
} else {
  $site_table = 'ProducerClipSite';
  $template->param(order_clips => 1);
  $template->param(order_pixxx => 0);
  $template->param(order_videos => 0);
  $IsClipOrder = 1;
}

$dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
$sth = $dbh->prepare("select * from $site_table where SiteID = '" . esc($q->param('storeid')) . "'");
if (!defined($sth) || !$sth->execute()) {print "\n(select site info) STH: " . $dbh->errstr . "<br>\n"; die;}
while (my $row_ref = $sth->fetchrow_hashref()) {
  $gizmo_g = $row_ref->{'g'};
  $template->param(store_title   => $row_ref->{'Title'});
  $template->param(bgcolor       => $row_ref->{'BGColor'});
  $template->param(text          => $row_ref->{'TextColor'});
  $template->param(link          => $row_ref->{'LinkColor'});
  $template->param(vlink         => $row_ref->{'VLinkColor'});
  $template->param(default_ship  => $row_ref->{'default_ship'}) if $site_table eq 'ProducerVideoSite';
  $ctry_ship{'default'}          =  $row_ref->{'default_ship'} if $site_table eq 'ProducerVideoSite';
  for ($domain) {
    /zapya/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'Clips4Sale');
      last;
    };
    /clips4sale/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'Clips4Sale');
      last;
    };
    /hanmanagement/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'HanManagement');
      $template->param(my_store_address => 'hanamangement.com');
      last;
    };
    /videos4sale/i && do {
      $template->param(storeback => '#FFEEDD');
      $template->param(headback => '#FFDDAA');
      $template->param(my_store => 'Videos4Sale');
      last;
    };
    /pixxx4sale/i && do {
      $template->param(storeback => '#CC9999');
      $template->param(headback => '#CC7777');
      $template->param(my_store => 'Images4Sale');
      last;
    };
    /images4sale/i && do {
      $template->param(storeback => '#CC9999');
      $template->param(headback => '#CC7777');
      $template->param(my_store => 'Images4Sale');
      last;
    };
    /sun-tropic/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'SuncoastProductions');
      $template->param(my_store_address => 'SuncoastProductions.biz');
      last;
    };
    /suncoastproductions/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'SuncoastProductions');
      $template->param(my_store_address => 'SuncoastProductions.biz');
      last;
    };
    /aigproductions/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'aigproductions.biz');
      $template->param(my_store_address => 'aigproductions.biz');
     last;
    };
    /sleepy-hollow/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'sleepy-hollow.biz');
      $template->param(my_store_address => 'sleepy-hollow.biz');
     last;
    };
    /adam700/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'adam700.com');
      $template->param(my_store_address => 'adam700.com');
     last;
    };

    /azrael-inc/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'azrael-inc.com');
      $template->param(my_store_address => 'azrael-inc.com');
     last;
    };
    /bpproductions/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'bpproductions.net');
      $template->param(my_store_address => 'bpproductions.net');
     last;
    };
    /ssfusa/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'ssfusa.biz');
      $template->param(my_store_address => 'ssfusa.biz');
     last;
    };
    /j-richardson/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'j-richardson.biz');
      $template->param(my_store_address => 'j-richardson.biz');
     last;
    };
    /pink-productions/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'pink-productions.com');
      $template->param(my_store_address => 'pink-productions.com');
     last;
    };
    /balaiinternational/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'balaiinternational.com');
      $template->param(my_store_address => 'balaiinternational.com');
     last;
    };
    /gg-productions/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'gg-productions.biz');
      $template->param(my_store_address => 'gg-productions.biz');
     last;
    };
    /bobbiephillips/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'bobbiephillips.biz');
      $template->param(my_store_address => 'bobbiephillips.biz');
     last;
    };
    /bjorkmantranstech/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'bjorkmantranstech.com');
      $template->param(my_store_address => 'bjorkmantranstech.com');
     last;
    };
    /newimageus/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'newimageus.com');
      $template->param(my_store_address => 'newimageus.com');
     last;
    };
    /wilowskimanagement/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'wilowskimanagement.biz');
      $template->param(my_store_address => 'wilowskimanagement.biz');
     last;
    };
    /srkenterprises/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'srkenterprises.biz');
      $template->param(my_store_address => 'srkenterprises.biz');
     last;
    };
    /tropical-productions/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'tropical-productions.com');
      $template->param(my_store_address => 'tropical-productions.com');
     last;
    };
    /sun-tropic/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'sun-tropic.com');
      $template->param(my_store_address => 'sun-tropic.com');
     last;
    };
    /tropic-diamond/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'tropic-diamond.com');
      $template->param(my_store_address => 'tropic-diamond.com');
     last;
    };
    /tropic-gold/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'tropic-gold.com');
      $template->param(my_store_address => 'tropic-gold.com');
     last;
    };
    /tropic-jewel/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'tropic-jewel.com');
      $template->param(my_store_address => 'tropic-jewel.com');
     last;
    };
    /sun-gold/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'sun-gold.biz');
      $template->param(my_store_address => 'sun-gold.biz');
     last;
    };
    /balaimanagement/i && do {
      $template->param(storeback => '#CFB0ED');
      $template->param(headback => '#BFA0DC');
      $template->param(my_store => 'balaimanagement.com');
      $template->param(my_store_address => 'balaimanagement.com');
     last;
    };



                                  
    
    /srkcneil/i && do {
      $template->param(storeback => '#FFEEEE');
      $template->param(headback => '#FFDDDD');
      $template->param(my_store => 'Scotty');
      last;
    };
    /prepa/ && do {
      $template->param(storeback => '#FFCC00');
      $template->param(headback => '#FFBB00');
      $template->param(my_store => 'PrePaidClips');
      last;
    };
  };
}
$sth->finish();

if ($q->param('GizmoOrder')){
        $gizmo_g = 1;
}

my @clipids;
foreach my $id (@id) {
  my %row_data = (thisclipid => $id);
  push @clipids, \%row_data;
}
$template->param(clipids          => \@clipids);
$template->param(remote_host      => $remote_host);
$template->param(remote_addr      => $remote_addr);
$template->param(remote_country   => $remote_country);
$template->param(http_user_agent  => $http_user_agent);
$template->param(form_tag         => $q->start_form(-id => 'POS_Order', -name => 'POS_Order'));
$template->param(descriptor       => $descriptor);
$template->param(storeid          => $storeid);
$template->param(customer_id      => $customer_id);
$template->param(session          => $rande);
$template->param(ip               => $remote_addr);
$template->param(referrer          => $referrer);
$template->param(CampaignCode          => $CampaignCode);
$template->param(TransID          => $transID);
$template->param(Ebill      => $eurobill);

if ($IsClipOrder == 1 ) {
  my $returnval;
  foreach my $id (@id) {
    if ($id ne '') {$returnval .= "&id=$id";}
  }
  $template->param(continueshopping  => 1);
  $template->param(returnval => $returnval);
}

#if (!defined $umkey and !defined $ePNAccount and !defined $goEMerch and !defined $authNname and !defined $linkPconfig and !defined $cpstnID) {
  #$error = "We are experiencing problems with the checkout system.  This store is still unable to process orders.  We will be back up soon...";
  #Main();
  #exit;
#}

if ($q->param('CheckOut') eq 'Cam_Order' and ($storeid == 37099 or $storeid == 37320)) {
  $error = " This studio is currently unable to accept additional memberships.  We appologize for the inconvenience";
  Main();
  exit;
}

if ($remote_addr =~ /^172\./ && !($remote_addr =~ /^172.1/)) {
  $error = " We are experiencing a techinical issue with our checkout system.  Please try again later to access the system.";
  Main();
  exit;
}

if ($gizmo_g == 1 or !defined($cc)) {
#if ($gizmo_g ne 0) { #Removed 9-24-2008 CHAGEN
  #if (!$pay_method) {$template->param(show_method_js => 'pay_by_gizmo();');} # Added by Ice Demon
  $template->param(has_cc           => 0);
} elsif ($pay_method eq "ClipCash") {
        $template->param(has_cc           =>0);
}
  else{
  $template->param(has_cc           => 1);
}
$template->param(prepaid => 1) if $gizmo_g == 1;
$template->param(show_method_js => 'pay_by_cc();') if $pay_method eq 'CC';
$template->param(show_method_js => 'pay_by_cc();') if ($pay_method eq '' and $gizmo_g != 1 and defined($cc));
$template->param(show_method_js => 'pay_by_gizmo();') if $pay_method eq 'GizmoCard' or $gizmo_g == 1;
$template->param(show_method_js => 'pay-by_clipcash();') if $pay_method eq 'ClipCash';

if ($q->param('Pay_Order')) {
  # cust info s/b filled in, submitting for payment
  if (!defined $q->param('PolicyAgree') or $q->param('PolicyAgree') ne "Iagree") {
    $error = "You must affirm your agreement with our refund policy in order to complete this purchase!.";
    Main();
    exit;
  }
  #NODUPES
my $printthis = '';
my $CheckSONumber = '';
my $FlagDupe = '0';
if ($q->param('CheckOut') eq '1'){
my $dbhSND = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
my $dbhND = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
    my $sthND = $dbhSND->prepare("
      select SONumber
      from ConsumerOrder
      where CustomerID = '$customer_id' and Order_Date > NOW() - interval 30 minute
        order by SONumber desc limit 1
      ");

    $sthND->execute();
    while (my $row_ref = $sthND->fetchrow_hashref()) {
      $CheckSONumber = $row_ref->{'SONumber'};
        my $sql = "select TransID from ProducerDetails where TransID = $CheckSONumber and ClipID in (1234 ";
        foreach my $ids (@id){
    $ids =~ s/ //g;
    if ($ids ne ''){
                $sql .= ", $ids ";
    }
        }
        $sql .= ")";
        my $sth2ND = $dbhND->prepare($sql);
        $sth2ND->execute();
        while (my $row_ref = $sth2ND->fetchrow_hashref()) {
         $FlagDupe = 1;
        }
        $sth2ND->finish();
        $printthis .= "$sql          $FlagDupe";

        #Check Each ID Ordered for Each Order placed against the ProducerDetails Table to monitor duplicates#

    }
   $sthND->finish;
   $dbhSND->disconnect;
   $dbhND->disconnect;
} 
if ($CheckSONumber ne '' && $FlagDupe == 1){
  #die "I died at this point $printthis";
  $error = "You have Already purchased one or more of these clips in the last 30 minutes";
  Main();
  exit;
}

#LIMIT ORDERS BY TIME
my $dbhSND = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
my $sthND = $dbhSND->prepare("
      select SONumber
      from ConsumerOrder
      where Order_Date > NOW() - interval 3 minute and IPAddress = inet_aton('$remote_addr')
      ");

$sthND->execute();
my $CheckPreviousOrder = '';
while (my $row_ref = $sthND->fetchrow_hashref()) {
     $CheckPreviousOrder = $row_ref->{'SONumber'};
}
$sthND->finish;
$dbhSND->disconnect;
if ($CheckPreviousOrder ne '') {
  $error = "Please allow 3 minutes between orders.";
  Main();
  exit;
} 

  if ($pay_method eq 'CC') {
    Check();
  }
  if ($pay_method eq 'ClipCash'){
    CheckClipCash();
  }
  Pay();
} else{
  
  # first display, cust info blank
  ## print "<html><head><title>Server Upgrade in progress</title></head><body><h2>Server upgrade in progress - we'll be back soon</h2></body></html>";
  ## exit;
  Main();
}

sub Denied {
  # check 1 hard coded IP address
  if ($remote_addr == 'notusedanymore') {
    $mailer->open({
        Subject => 'FRAUD CPROD3 IP',
        To => 'fraud@intermarkproductions.com',
        From => 'info@' . $the_domain
      });
    print $mailer "IP: " . $remote_addr . "\n";
    print $mailer "Country from IP: " . $remote_country . "\n";
    my @names = $q->param;
    foreach my $names (@names) {
      chomp $names;
  if ($names =~ /Credit_Card_Number/i or $names =~ /cvv/i or $names =~ /cvm/i or $names =~ /email/i) {}
                                else{

      print $mailer $names . ": " . $q->param($names) . "\n";
  }
    }
    $mailer->close;
    $error = "Your Order can not be completed without contacting Customer Support at 727 498 8515 or info\@" . $the_domain . " (err-aaa)";
    Main();
    exit;
  }

  # check 2 hard coded email address
  if ($q->param('Email') =~ /\@nifty\.com|jwunsch2|MAGIX5|\@sol\.com|khoaibopco|ycc\.chi|erika_babe6|arnie_466|yccchiyihyii|tony_soprano777|zzaretta100|cenac|\@mails\.com|beatbran89|ryousuke|thichbopco|khoaku|msangerl|trueaznboi|epsviver|QPWOALSKZMXN321|viperfred03|paul\@dfe\.com|renard\_tas|epsviver|phhhh|ngocloiluong|shaonuk/gi) 
{
    $mailer->open({
        Subject => 'FRAUD CPROD3 EMAIL',
        To => 'fraud@intermarkproductions.com',
        From => 'info@' . $the_domain
      });
    print $mailer "Email: " . $q->param('Email') . "\n";
    print $mailer "IP: " . $remote_addr . "\n";
    print $mailer "Country from IP: " . $remote_country . "\n";
    my @names = $q->param;
    foreach my $names (@names) {
      chomp $names;
  if ($names =~ /Credit_Card_Number/i or $names =~ /cvv/i or $names =~ /cvm/i or $names =~ /email/i) {}
                                else{

      print $mailer $names . ": " . $q->param($names) . "\n";
  }
    }
    $mailer->close;
    $error = "Your Order can not be completed without contacting Customer Support at  727 498-8515 or info\@" . $the_domain . " (err-acd)";
    Main();
    exit;
  }

#  # check 3 bogus email address
#  if ($q->param('Email') =~ /^(asd|dsf).*/gi) {
#    $mailer->open({
#        Subject => 'FRAUD CPROD3 EMAIL2',
#        To => 'info@intermarkproductions.com',
#        From => 'info@' . $the_domain
#      });
#    print $mailer "Email: " . $q->param('Email') . "\n";
#    print $mailer "IP: " . $remote_addr . "\n";
#    print $mailer "Country from IP: " . $remote_country . "\n";
#    my @names = $q->param;
#    foreach my $names (@names) {
#      chomp $names;
#      print $mailer $names . ": " . $q->param($names) . "\n";
#    }
#    $mailer->close;
#    $error = "Please contact customer support at  727-498-8515 or info\@" . $the_domain . " (err-aeg)";
#    Main();
#    exit;
#  }

  # check 4 fraud database
   if ($q->param('Email') !~ /ThisisAllowed3v3nth0ugh1tshouldn0tb3|christemp97\@hagenweb.org/gi) {
  my $fraud_name = lc($q->param('Full_Name'));
  my $fraud_email = lc($q->param('Email'));
   my $dbz = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
  #my $dbz = DBI->connect("DBI:mysql:paywide:ice.paywide.com", 'janey', 'Bjorkman6');
  if (!defined($dbz)) {$error = "There has been a internal error with this process 1"; Main(); exit;}
  
  my $stz = $dbz->prepare("
    SELECT * FROM fraud 
    WHERE deleted = 0 and 
      ( 
      cardnumber = aes_encrypt(" . $dbz->quote($credit_card) . ", '$ccEncryptString') OR 
      name = aes_encrypt(" . $dbz->quote($fraud_name) . ", '$nameEncryptString') OR 
      email LIKE aes_encrypt(" . $dbz->quote($fraud_email) . ", '$emailEncryptString') OR
      ip LIKE " . $dbz->quote($remote_addr) . ")"   
  );
#if (!defined($stz) || !$stz->execute()) {$error = "There has been a internal error with this process"; Main(); exit;}
  if (defined($stz) && $stz->execute()) {
    if ($stz->rows()) {
      $mailer->open({
        Subject => 'FRAUD CPROD3 PAYWIDE FRAUD DB',
        To => 'fraud@intermarkproductions.com',
        From => 'info@' . $the_domain
      });
      while (my $row_refz = $stz->fetchrow_hashref()) {
        if (defined $row_refz->{'cardnumber'} and $credit_card eq $row_refz->{'cardnumber'}) {
          print $mailer "Credit Card Match: d\n";
        }
                                if (defined $row_refz->{'name'} and $fraud_name eq $row_refz->{'name'}) {
                                        print $mailer "Name: $fraud_name\n";
                                }
        if (defined $row_refz->{'email'} and $q->param('Email') eq $row_refz->{'email'}) {
          print $mailer "Email: " . $q->param('Email') . "\n";
        }
        if (defined $row_refz->{'ip'} and $remote_addr eq $row_refz->{'ip'}) {
          print $mailer "IP: " . $remote_addr . "\n";
          print $mailer "Country from IP: " . $remote_country . "\n";
        }
      }
      print $mailer "\n";
      my @names = $q->param;
                        my $fraudOrderData = "This is the Order Information\n\n";
      foreach my $names (@names) {
        chomp $names;
  if ($names =~ /Credit_Card_Number/i or $names =~ /cvv/i or $names =~ /cvm/i or $names =~ /email/i) {}
                                else{

      print $mailer $names . ": " . $q->param($names) . "\n";
  }

                                if ($names =~ /Credit_Card_Number/i or $names =~ /cvv/i or $names =~ /cvm/i) {}
                                else{
                                        $fraudOrderData .= "$names : ". $q->param($names) . "\n";
                                }
      }
      $mailer->close;
                        
                        
                        
      # Get the aes value from the db w/a select. Then use the val for the INSERT.

      my $enc_val_cc = Encrypt($credit_card, $ccEncryptString);
      my $enc_val_full_name = Encrypt($q->param('Full_Name'), $nameEncryptString);  
      my $enc_val_email = Encrypt($q->param('Email'), $emailEncryptString); 
      
                        #insert into the fraud table
                        my $fraudSQL = "insert into Track_Fraud 
                        set Credit_Card = '" . esc($enc_val_cc) . "',
                        Name = '" . esc($enc_val_full_name) . "',
                        Email = '" . esc($enc_val_email) . "',
                        ProducerID = " . $q->param('storeid') . ",
                        Amount = " . $q->param('Grand_Total') . ",
                        IPAddress = inet_aton('$remote_addr'),
                        FraudSystem = 'PAYWIDE',
                        OrderDetails = '" . esc($fraudOrderData) . "',
                        Max_AnonymousProxy = '$anonymousProxy',
                        Max_Country = '$MaxCountry',
                        Max_Distance = '$MaxDistance',
                        Max_HighRiskCountry = '$MaxHighRisk',
                        Max_IP_Region = '$MaxIPRegion',
                        Max_MaxMindID = '$MaxID',
                        Max_ProxyScore = 0,
                        Max_Score = 0,
                        Max_IP_ISP = '$MaxISP',
                        Max_IP_ORG = '$MaxORG',
                        MaxMindDetails = '$maxmind_ccfs_info',
                        Fraud_Flag = 0,
      Service = '$service'";
      
    

  $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
  $sth = $dbhS->prepare($fraudSQL);
  if (!defined($sth) || !$sth->execute()) {print "\n(Could not add Paywide fraud data to Track_Fraud) <br>\n"; die;}
  $sth->finish;
  $dbhS->disconnect();


      $error = "Your Order can not be completed without contacting Customer Support at  727 498-8515 or info\@" . $the_domain . " (err-aey)";
      Main();
      exit;
    }
      $stz->finish();
    $dbz->disconnect();
  }
  }

  # check 5 maxmind.com cc fraud detect
  use Business::MaxMind::CreditCardFraudDetection;

  # Constructor parameters:
  #  isSecure = 1 then use Secure HTTP
  #  debug    = 0 then print no debuging info
  #  timeout    time in seconds to wait before timing out and returning
  my $ccfs = Business::MaxMind::CreditCardFraudDetection->new(isSecure => 1, debug => 0, timeout => 9);
  my $license_key = 'oVdZKQi6c9Bn';
  my $edomain      = $q->param('Email');
  $edomain         =~ s/^.*@//;
  my $bin          = substr($credit_card,0,6);
  my $forwarded_ip = $ENV{'HTTP_X_FORWARDED_FOR'};
  $forwarded_ip    = $ENV{'HTTP_CLIENT_IP'} unless $forwarded_ip;
  my $thissession  = $q->param('Session');
  $thissession     = $rande unless $thissession;
  my $creditbank   = $q->param('Credit_Card_Bank') || '';
  my $creditphone  = $q->param('Credit_Card_Phone') || '';
  my $homephone    = $q->param('Customer_Phone') || '';
  $ccfs->input(
    # required fields
    i => $remote_addr,
    city => $q->param('City'),
    region => $q->param('State'),
    postal => $q->param('Zip_Code'),
    country => $q->param('Country'),

    # recommended fields
    domain => $edomain,
    bin => $bin,
    custPhone => $homephone,
    forwardedIP => $forwarded_ip,
    license_key => $license_key,

    # optional fields
    binName => $creditbank,
    binPhone => $creditphone,
    requested_type => 'premium',
    # Business::MaxMind::CreditCardFraudDetection will take
    # MD5 hash of e-mail address passed to emailMD5 if it
    # detects '@' in the string
    emailMD5 => $q->param('Email'),
    shipAddr => '',
    txnID => $rande,
    sessionID => $thissession
  );
  $ccfs->query;
  my $ccfs_ref = $ccfs->output;
  $proxyScore  = $ccfs_ref->{'proxyScore'} || 0;
  $spamScore   = $ccfs_ref->{'spamScore'} || 0;
  $score       = $ccfs_ref->{'score'} || 0;

  $anonymousProxy = $ccfs_ref->{'anonymousProxy'} || 'NA';
  $MaxCountry = $ccfs_ref->{'binCountry'} || 'NA';
  $MaxDistance = $ccfs_ref->{'distance'} || 0;
  $MaxHighRisk = $ccfs_ref->{'highRiskCountry'} || 'NA';
  $MaxIPRegion = $ccfs_ref->{'id_region'} || 'NA';
  $MaxID = $ccfs_ref->{'maxmindID'} || 'NA';
  $MaxISP = $ccfs_ref->{'ip_isp'} || 'NA';
  $MaxORG = $ccfs_ref->{'ip_org'} || 'NA';
  $MaxCity = $ccfs_ref->{'ip_city'} || 'NA';
  $MaxState = $ccfs_ref->{'ip_region'} || 'NA';
  $MaxSpamScore = $ccfs_ref->{'spamScore'} || 'NA';
  
  
  
  $maxmind_ccfs_info .= "MaxMind.com Credit Card Fraud Detection info:\n";
  foreach my $key (sort keys %{$ccfs_ref}) {
    $maxmind_ccfs_info .= sprintf "%28s=> %s\n", $key, $ccfs_ref->{$key};
  }
  $maxmind_ccfs_info .= sprintf "%28s=> %s\n", 'forwarded_ip', $forwarded_ip if defined $forwarded_ip;

  # can sometime come back blank, so require > 0
  if ( $ccfs_ref->{'queriesRemaining'} > 0 and $ccfs_ref->{'queriesRemaining'} < 1501 and $ccfs_ref->{'queriesRemaining'}%100 == 0) {
    # notify every 100 maxmind queries if remaining count <= 1500
    $mailer->open({
        Subject => 'MAXMIND SUBSCRIPTION RUNNING LOW',
        To => 'fraud@intermarkproductions.com',
        From => 'info@' . $the_domain
      });
    print $mailer "There are only " . $ccfs_ref->{'queriesRemaining'} . "queries remaining in your MaxMind account.\n\n";
    print $mailer "Check the MaxMind website for the auto-renewal date, and if it is later than tomorrow increase the subscription to the next level.\n";
    $mailer->close;
  }
  if ( $ccfs_ref->{'score'} > 7.50 || $ccfs_ref->{'carderEmail'} =~ /^y/i ) {
    # maxmind says likely fraud. 1st check for manual override; if not, then provide additional fields to help lower score
    $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
    my $mmsum = $dbhS->selectrow_array("select count(*) from MaxMindOverrideEmailAddresses where Email = '".$q->param('Email')."'");
    if (!defined $mmsum or $mmsum == 0) {
      if ($creditbank) {
        # assume from the presence of creditbank that we also have creditphone and homephone, and still got a too-high score. Deny.
        $mailer->open({
            Subject => 'FRAUD CPROD3 MAXMIND',
            To => 'fraud@intermarkproductions.com',
            From => 'info@' . $the_domain
          });
        print $mailer "Email: " . $q->param('Email') . "\n";
        print $mailer "IP: " . $remote_addr . "\n";
        print $mailer "Country from IP: " . $remote_country . "\n\n";
        print $mailer $maxmind_ccfs_info . "\n";
        my @names = $q->param;
        my $fraudOrderData = "This is the Order Information\n\n";
        foreach my $names (@names) {
          chomp $names;
          if ($names =~ /Credit_Card_Number/i or $names =~ /cvv/i or $names =~ /cvm/i or $names =~ /email/i) {}
          else{
          print $mailer $names . ": " . $q->param($names) . "\n";
            $fraudOrderData .= "$names : ". $q->param($names) . "\n";
          }
        }
        $mailer->close;
        
        # Get the aes value from the db w/a select. Then use the val for the INSERT.
        my $enc_val_cc = Encrypt($q->param('Credit_Card_Number'), $ccEncryptString);
        my $enc_val_full_name = Encrypt($q->param('Full_Name'), $nameEncryptString);  
        my $enc_val_email = Encrypt($q->param('Email'), $emailEncryptString); 
        
      
        #insert into the fraud table
        my $fraudSQL = "insert into Track_Fraud 
                        set
                        Credit_Card = '" . esc($enc_val_cc) . "',
                        Name = '" . esc($enc_val_full_name) . "',
                        Email = '" . esc($enc_val_email) . "',
                        ProducerID = " . $q->param('storeid') . ",
                        Amount = " . $q->param('Grand_Total') . ",
                        IPAddress = inet_aton('$remote_addr'),
                        FraudSystem = 'MaxMind',
                        OrderDetails = '" . esc($fraudOrderData) . "',
                        Max_AnonymousProxy = '$anonymousProxy',
                        Max_Country = '$MaxCountry',
                        Max_Distance = '$MaxDistance',
                        Max_HighRiskCountry = '$MaxHighRisk',
                        Max_IP_Region = '$MaxIPRegion',
                        Max_MaxMindID = '$MaxID',
                        Max_ProxyScore = $proxyScore,
                        Max_Score = $score,
                        Max_IP_ISP = '$MaxISP',
                        Max_IP_ORG = '$MaxORG',
                        MaxMindDetails = '$maxmind_ccfs_info',
                        Fraud_Flag = 0,
      Service = '$service'";
                                 

  $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
  $sth = $dbhS->prepare($fraudSQL);
  if (!defined($sth) || !$sth->execute()) {print "\n(Could not add MaxMind fraud data to Track_Fraud) <br>\n"; die;}
  $sth->finish;
  $dbhS->disconnect();
                
        $error = "Your Order can not be completed without contacting Customer Support at  727-498-8515 or info\@" . $the_domain . " (err-afq)";
        Main();
        exit;
      } else {
        # not good, but may be salvageable by getting creditbank, creditphone, and homephone
        $cc_addl_reqd = 1;
        $error = "Please enter additional information below";
        Main();
        exit;
      }
    }
  }

  # check 6 rate limit
  $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
  # Get the aes value from the db w/a select. Then use the val for the INSERT.
  my $enc_val_cc = Encrypt($credit_card, $ccEncryptString);
        
  my $stl = $dbhS->prepare("select count(*) from RateLimitCC where card = " . $dbhS->quote($enc_val_cc) . " and last_use > NOW() - interval 30 minute");
  my $usecount = 0;
  if (!defined($stl) || !$stl->execute()) {$error = "There has been a internal error with this process 3"; Main(); exit;}
  $stl->bind_columns(\$usecount);
  $stl->fetch();
  $stl->finish();
  if ($usecount > 2 && $q->param('Email') !~ /52chevytruck/gi) {
    $usecount++;
    $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
    
    $dbhS->do("replace into RateLimitCC set card = '$enc_val_cc', last_use = NOW()");
    $mailer->open({Subject => 'RATELIMIT CPROD3',
        To => 'fraud@intermarkproductions.com',
        From => 'info@' . $the_domain
      });
    print $mailer "Check RateLimit data  attempted $usecount times in 30 minutes\n";
    print $mailer "IP: " . $remote_addr . "\n";
    print $mailer "Country from IP: " . $remote_country . "\n";
    my @names = $q->param;
    foreach my $names (@names) {
      chomp $names;
    
   if ($names =~ /Credit_Card_Number/i or $names =~ /cvv/i or $names =~ /cvm/i or $names =~ /email/i) {}
                                else{

      print $mailer $names . ": " . $q->param($names) . "\n";
        }

    }
    $mailer->close;
    $error = "You have exceeded our limit of 3 denied/declined attempts in 30 minutes. Please wait 30 minutes before trying again or contact customer support at  727-498-8515 or info\@" . $the_domain . " (err-afz)";
    Main();
    exit;
  }
  
}

sub CheckClipCash {

  my $fraud_name = lc($q->param('clipcash_name'));
  my $fraud_email = lc($q->param('clipcash_email'));
        my $clipcash_number = $q->param('clipcash_number');

  if ($q->param('clipcash_name') eq '') {
    $error = "You must enter a valid name.\n (err-ccn)";
    Main();
    exit;
  }
  if ($q->param('clipcash_number') eq '') {
    $error = "You must enter a valid ClipCash Number.\n (err-ccc)";
    Main();
    exit;
  }
  if ($q->param('clipcash_email') !~ /[[:alnum:]\.\!\#\$\%\&\'\*\+\/\=\?\^\_\`\{\}\|\~\-]+@(?:[[:alnum:]\-]+\.)+[[:alpha:]]{2,6}/i) {
    $error = "You must enter a valid email address.\n (err-cce)";
    Main();
    exit;
  }


   my $dbz = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
  #my $dbz = DBI->connect("DBI:mysql:paywide:ice.paywide.com", 'janey', 'Bjorkman6');
  if (!defined($dbz)) {$error = "There has been a internal error with this process 4"; Main(); exit;}
  my $stz = $dbz->prepare("
    SELECT * FROM fraud 
    WHERE deleted = 0 and 
      ( 
      cardnumber = aes_encrypt(" . $dbz->quote($clipcash_number) . ", '$ccEncryptString') OR 
      name = aes_encrypt(" . $dbz->quote($fraud_name) . ", '$nameEncryptString') OR 
      email LIKE aes_encrypt(" . $dbz->quote($fraud_email) . ", '$emailEncryptString') OR
      ip LIKE " . $dbz->quote($remote_addr) . ")"
  );
#if (!defined($stz) || !$stz->execute()) {$error = "There has been a internal error with this process"; Main(); exit;}
  if (defined($stz) && $stz->execute()) {
    if ($stz->rows()) {
      $mailer->open({
        Subject => 'FRAUD PAYWIDE DB Match clip order (ClipCashAccount)',
        To => 'fraud@intermarkproductions.com',
        From => 'info@' . $the_domain
      });
      while (my $row_refz = $stz->fetchrow_hashref()) {
        print $mailer "Matched ID: ", $row_refz->{'id'} , "\n";
        if (defined $row_refz->{'cardnumber'} and $clipcash_number eq $row_refz->{'cardnumber'}) {
          print $mailer "ClipCash Card Match: d\n";
        }
                                if (defined $row_refz->{'name'} and $fraud_name eq $row_refz->{'name'}) {
                                        print $mailer "Name Match: $fraud_name\n";
                                }
        if (defined $row_refz->{'email'} and $fraud_email eq $row_refz->{'email'}) {
          print $mailer "Email Match: $fraud_email\n";
        }
        if (defined $row_refz->{'ip'} and $remote_addr eq $row_refz->{'ip'}) {
          print $mailer "IP Match: " . $remote_addr . "\n";
          print $mailer "Country from IP: " . $remote_country . "\n";
        }
      }
      print $mailer "\n";
      my @names = $q->param;
                        my $fraudOrderData = "This is the Order Information\n\n";
      foreach my $names (@names) {
        chomp $names;
  if ($names =~ /Credit_Card_Number/i or $names =~ /cvv/i or $names =~ /cvm/i or $names =~ /email/i) {}
                                else{

      print $mailer $names . ": " . $q->param($names) . "\n";
  }

                                if ($names =~ /Credit_Card_Number/i or $names =~ /cvv/i or $names =~ /cvm/i) {}
                                else{
                                        $fraudOrderData .= "$names : ". $q->param($names) . "\n";
                                }
      }
      $mailer->close;
      
      # Get the aes value from the db w/a select. Then use the val for the INSERT.
      my $enc_val_clipcash = Encrypt($clipcash_number, $ccEncryptString);
      my $enc_val_name = Encrypt($fraud_name, $nameEncryptString);  
      my $enc_val_email = Encrypt($fraud_email, $emailEncryptString);
      
                        #insert into the fraud table
                        my $fraudSQL = "insert into Track_Fraud 
                        set
                        Credit_Card = '" . esc($enc_val_clipcash) . "',
                        Name = '" . esc($enc_val_name) . "',
                        Email = '" . esc($enc_val_email) . "',
                        ProducerID = " . $q->param('storeid') . ",
                        Amount = " . $q->param('Grand_Total') . ",
                        IPAddress = inet_aton('$remote_addr'),
                        FraudSystem = 'PAYWIDE',
                        OrderDetails = '" . esc($fraudOrderData) ."',
                        Max_AnonymousProxy = '',
                        Max_Country = '',
                        Max_Distance = '',
                        Max_HighRiskCountry = '',
                        Max_IP_Region = '',
                        Max_MaxMindID = '',
                        Max_ProxyScore = 0,
                        Max_Score = 0,
                        Max_IP_ISP = '',
                        Max_IP_ORG = '',
                        MaxMindDetails = '',
                        Fraud_Flag = 0,
      Service = '$service'";
      
    

  $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
  $sth = $dbhS->prepare($fraudSQL);
  if (!defined($sth) || !$sth->execute()) {print "\n(Could not add Paywide fraud data to Track_Fraud) <br>\n"; die;}
  $sth->finish;
  $dbhS->disconnect();


      $error = "Your Order can not be completed without contacting Customer Support at  727-498-8515 or info\@" . $the_domain . " (err-aey)";
      Main();
      exit;
    }
      $stz->finish();
    $dbz->disconnect();
  }
}


sub Main {
  my $oldid = 0;
  my $cliptotal = 0;
  my $clipfmt = '';
  my $imagefmt = '';
  my @itemlist;
  $template->param(needAddl => $cc_addl_reqd);
  $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
  foreach my $id (sort @id) {
    next if $oldid eq $id;
    $oldid = $id;
     $id =~ s/[a-z]//ig;
     $id =~ s/'//ig;
     $id =~ s/=//ig;
     $id =~ s/<>//ig;
#qqq
    if ($q->param('CheckOut') eq 'Order Videos') {
      ($id, $clipfmt) = split /:/, $id;
      $sth = $dbh->prepare("select * from StoreProducerVideos where VideoID = '$id' and ProducerID = '" . $q->param('storeid') . "'");
      if (!defined($sth) || !$sth->execute()) {print "\n(select video from videos) STH: " . $dbh->errstr . "<br>\n"; die;}
      while (my $row_ref = $sth->fetchrow_hashref()) {
        my %row_data = (item => $row_ref->{'VideoTitle'}, itemprice => sprintf("%.2f",$row_ref->{'VideoPrice'}), itemfmt => $clipfmt, clipid => "$id-$clipfmt");
        if ($row_ref->{'VideoID'}) {
          $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
          my $st2 = $dbh->prepare("select VideoID from ProducerDetails where VideoID = '" . $row_ref->{'VideoID'} . "' and CustomerID = '" . $customer_id . "'");
          if (!defined($st2) || !$st2->execute()) {die "\n(select video from details) STH: " . $dbh->errstr . "<br>\n";}
          my $bought_id;
          $st2->bind_columns(\$bought_id);
          $st2->fetch();
          if (defined $bought_id and $bought_id == $row_ref->{'VideoID'}) {
            $row_data{'bought_it'} = 1;
          } else {
            $row_data{'bought_it'} = 0;
          }
          push @itemlist, \%row_data;
          $cliptotal += $row_ref->{'VideoPrice'};
        }
      }
    } elsif ($q->param('CheckOut') eq 'Order Pixxx') {
      $sth = $dbh->prepare("select * from StoreProducerImages where ImageID = '$id' and ProducerID = '" . $q->param('storeid') . "'");
      if (!defined($sth) || !$sth->execute()) {print "\n(select image from images) STH: " . $dbh->errstr . "<br>\n"; die;}
      while (my $row_ref = $sth->fetchrow_hashref()) {
        $imagefmt = uc $row_ref->{'Num_Of_Files'};
        $imagefmt =~ s/^.*\.//;
        my %row_data = (item => $row_ref->{'ImageTitle'}, itemprice => sprintf("%.2f",$row_ref->{'ImagePrice'}), itemfmt => $imagefmt, clipid => $id);
        if ($row_ref->{'ImageID'}) {
          $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
          my $st2 = $dbh->prepare("select ImageID from ProducerDetails where ImageID = '" . $row_ref->{'ImageID'} . "' and CustomerID = '" . $customer_id . "'");
          if (!defined($st2) || !$st2->execute()) {die "\n(select image from details) STH: " . $dbh->errstr . "<br>\n";}
          my $bought_id;
          $st2->bind_columns(\$bought_id);
          $st2->fetch();
          if (defined $bought_id and $bought_id == $row_ref->{'ImageID'}) {
            $row_data{'bought_it'} = 1;
          } else {
            $row_data{'bought_it'} = 0;
          }
          push @itemlist, \%row_data;
          $cliptotal += $row_ref->{'ImagePrice'};
        }
      }
    } #CAMBILL
      elsif ($q->param('CheckOut') eq 'Cam_Order') {
        #Cam Orders
        my %row_data = (item => $camProductName , itemprice => sprintf("%.2f",$camPrice), itemfmt => $camUserName, clipid => '');
        #die "I have data $camProductName $camPrice $camUserName";
        push @itemlist, \%row_data;
        $cliptotal = $camPrice;
  #CAMBILL
  }
  else {
      # clips
      $sth = $dbh->prepare("select * from StoreProducerClips where ClipID = '$id' and ProducerID = '" . $q->param('storeid') . "'");
      if (!defined($sth) || !$sth->execute()) {print "\n(select clip from clips) STH: " . $dbh->errstr . "<br>\n"; die;}
      while (my $row_ref = $sth->fetchrow_hashref()) {
        $clipfmt = uc $row_ref->{'ClipName'};
        $clipfmt =~ s/^.*\.//;
        my %row_data = (item => $row_ref->{'ClipTitle'}, itemprice => sprintf("%.2f",$row_ref->{'ClipPrice'}), itemfmt => $clipfmt, clipid => $id);
        if ($row_ref->{'ClipID'}) {
          $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
          my $st2 = $dbh->prepare("select ClipID from ProducerDetails where ClipID = '" . $row_ref->{'ClipID'} . "' and CustomerID = '" . $customer_id . "'");
          if (!defined($st2) || !$st2->execute()) {die "\n(select clip from details) STH: " . $dbh->errstr . "<br>\n";}
          my $bought_id;
          $st2->bind_columns(\$bought_id);
          $st2->fetch();
          if (defined $bought_id and $bought_id == $row_ref->{'ClipID'}) {
            $row_data{'bought_it'} = 1;
          } else {
            $row_data{'bought_it'} = 0;
          }
          push @itemlist, \%row_data;
          $cliptotal += $row_ref->{'ClipPrice'};
        }
      }
    }
    $sth->finish();
  }
  $template->param(itemlist => \@itemlist) if @itemlist;

  $template->param(cliptotal   => sprintf "%.2f", $cliptotal);
  $template->param(grand_total => $cliptotal);

  my $cust_state = 'not gonna match';
  my $cust_c     = 'not gonna match';
  my $expire_mon = 'not gonna match';
  my $expire_yr  = 'not gonna match';
  if ($customer_id) {
    $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
    $sth = $dbhS->prepare("
      select FullName,AddressOne,AddressTwo,City,State,ZipCode,Country,Email
      from ConsumerOrderAddress
      where CustomerID = '$customer_id'
  order by SONumber desc limit 1
      ");
    $sth->execute();
    while (my $row_ref = $sth->fetchrow_hashref()) {
      $template->param(fullname   => $row_ref->{'FullName'});
      $template->param(addressone => $row_ref->{'AddressOne'});
      $template->param(addresstwo => $row_ref->{'AddressTwo'});
      $template->param(city       => $row_ref->{'City'});
      $cust_state                 =  $row_ref->{'State'};
      $template->param(zipcode    => $row_ref->{'ZipCode'});
      $cust_c                     =  $row_ref->{'Country'};
      $template->param(email      => $row_ref->{'Email'});
    }
    $sth->finish;
   $dbhS->disconnect;
  }
  if (!$template->param('fullname') and defined $q->param('Full_Name')) { $template->param(fullname   => $q->param('Full_Name')); }
  if (!$template->param('firstname') and defined $q->param('First_Name')) { $template->param(firstname   => $q->param('First_Name')); }
  if (!$template->param('lastname') and defined $q->param('Last_Name')) { $template->param(lastname   => $q->param('Last_Name')); }
  if (!$template->param('addressone') and defined $q->param('Address_1') ) { $template->param(addressone   => $q->param('Address_1')); }
  if (!$template->param('addresstwo') and defined $q->param('Address_2')) { $template->param(addresstwo   => $q->param('Address_2')); }
  if (!$template->param('city') and defined $q->param('City') ) { $template->param(city   => $q->param('City')); }
  if ($cust_state eq 'not gonna match' and defined $q->param('State')) { $cust_state = $q->param('State'); }
  if (!$template->param('zipcode') and defined $q->param('Zip_Code') ) { $template->param(zipcode   => $q->param('Zip_Code')); }
  if ($cust_c eq 'not gonna match' and defined $q->param('Country')) { $cust_c = $q->param('Country'); }
  if (!$template->param('email') and defined $q->param('Email')) { $template->param(email   => $q->param('Email')); }
  if (defined $q->param('CardName')) {
    if ($q->param('CardName') eq 'Visa')             { $template->param(v_sel => ' selected="selected"'); }
    if ($q->param('CardName') eq 'Mastercard')       { $template->param(m_sel => ' selected="selected"'); }
    if ($q->param('CardName') eq 'Discover')         { $template->param(d_sel => ' selected="selected"'); }
    if ($q->param('CardName') eq 'American Express') { $template->param(a_sel => ' selected="selected"'); }
  }
  if (!$template->param('creditcard') and defined $q->param('Credit_Card_Number')) { $template->param(creditcard   => $q->param('Credit_Card_Number')); }
  if ($expire_mon eq 'not gonna match' and defined $q->param('Expiration_Month_Card')) { $expire_mon = $q->param('Expiration_Month_Card'); }
  if ($expire_yr eq 'not gonna match' and defined $q->param('Expiration_Year')) { $expire_yr = $q->param('Expiration_Year'); }
  if ($q->param('cvmvalue')) { $template->param(cvmvalue => $q->param('cvmvalue')); }
  
  my @state_opts;
  foreach my $st_id (sort { $states{$a} cmp $states{$b} } keys %states) {
    my $selected = '';
    if ($st_id eq $cust_state) { $selected = '" selected="selected'; }
    my %row_data = (st_id => $st_id, st_name => $states{$st_id}, st_selected => $selected);
    push @state_opts, \%row_data;
  }
  $template->param(state_list => \@state_opts);

  my @country_opts;
  foreach my $c_name (sort { $a cmp $b } keys %countries) {
    my $selected = '';
    if ($cust_c eq 'not gonna match') {
      if ($countries{$c_name} eq 'US') { $selected = '" selected="selected'; }
    } else {
      if ($countries{$c_name} eq $cust_c) { $selected = '" selected="selected'; }
    }
    my %row_data = (c_name => $c_name, c_id => $countries{$c_name}, c_selected => $selected);
    push @country_opts, \%row_data;
  }
  $template->param(country_list => \@country_opts);

  my @exp_months;
  foreach my $exp_mon (1 .. 12) {
    $exp_mon = sprintf "%02u", $exp_mon;
    my $selected = '';
    if ($exp_mon eq $expire_mon) { $selected = ' selected="selected"'; }
    my %row_data = (exp_mon => $exp_mon, xm_selected => $selected);
    push @exp_months, \%row_data;
  }
  $template->param(expire_mon_list => \@exp_months);

  my @exp_years;
  foreach my $exp_yr (8 .. 25) {
    $exp_yr = sprintf "%02u", $exp_yr;
    my $selected = '';
    if ($exp_yr eq $expire_yr) { $selected = ' selected="selected"'; }
    my %row_data = (exp_yr => $exp_yr, xy_selected => $selected);
    push @exp_years, \%row_data;
  }
  $template->param(expire_yr_list => \@exp_years);
  if ($error ne ''){print $q->header();}
  $template->param(error => $error);
  print $template->output;
}

sub Pay {
  Denied() if $pay_method eq 'CC';

  my $paytot = $q->param('Grand_Total'); 
  #die $q->header() . "\n\nThis is the Grand Total :$paytot:";
  my %uniqcnt;
  # someone figured out how to buy 20 clips for $1
  # get min price for store, avg price per item
  my $sth;
  if ($q->param('CheckOut') eq 'Order Videos') {
    $sth = $dbh->prepare("select min(VideoPrice) as minPrice from StoreProducerVideos where ProducerID = $storeid");
  } elsif ($q->param('CheckOut') eq 'Order Pixxx') {
    $sth = $dbh->prepare("select min(ImagePrice) as minPrice from StoreProducerImages where ProducerID = $storeid");
  } #CAMBILL STUFF
    elsif ($q->param('CheckOut') eq 'Cam_Order') {
    $sth = $dbh->prepare("select 5");
  } else {
    $sth = $dbh->prepare("select min(ClipPrice)  as minPrice from StoreProducerClips  where ProducerID = $storeid");
  }
  if (!defined($sth) || !$sth->execute()) {print "\n(select minPrice) STH: " . $dbh->errstr . "<br>\n"; die;}
  my $minprice = $sth->fetchrow_array;
  $minprice = 2.98 unless $minprice;
  $minprice -= 0.005;
  @uniqids = grep { ++$uniqcnt{$_} < 2 } @id;
  my $avgprice = ($paytot / @uniqids) + 0.005;
 if ($OrderType eq 'Cam_Order'){ $avgprice = $paytot;}
  if ($avgprice < $minprice) {
    open LOG, ">> /home/OrderSystem/public_html/SecureProcess/usaepay.log";
    print LOG "\n\nREJECTED: ",($q->param('CheckOut'))," paytot $paytot / item count ",scalar @uniqids,": ",$paytot / @uniqids,"  minprice: $minprice\n";
    foreach my $itemid (@uniqids) {
      if ($OrderType ne 'Cam_Order') {
  print LOG $itemid->{'thisclipid'},$/;
      }
    }
    print LOG $/;
    close LOG;
    $error = "This transaction was rejected. (err-afu)";
    # Get the aes value from the db w/a select. Then use the val for the INSERT.
    my $enc_val_cc = Encrypt($credit_card, $ccEncryptString);
    
    $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
    $dbhS->do("replace into RateLimitCC set card = '$enc_val_cc', last_use = NOW()");
    send_deny_error('underpriced', $paytot, "average price $avgprice, min price $minprice", undef,undef,undef,undef,undef,undef,undef,undef);
    Main();
    exit;
  }
  if ($q->param('CheckOut') eq 'Order Videos') {
    # if video add shipping to total
    if (defined $ctry_ship{$q->param('Country')}) {
      $paytot += $ctry_ship{$q->param('Country')};
    } else {
      $paytot += $ctry_ship{'default'};
    }
  }

  #change this line and the one before for non test.
  #if ('a' eq 'a'){
  #     $error = "testing";
  #     Main();
  #     exit;
  #   }
  if ($pay_method eq 'GizmoCard' or $gizmo_g == 1) {
    pay_gizmo($paytot);
  } elsif ($pay_method eq 'ClipCash') {
         pay_clipcash($paytot);
  } elsif (defined $umkey) {
    pay_usaepay($paytot);
  } elsif (defined $ePNAccount) {
    pay_eproc($paytot);
  } elsif (defined $goEMerch) {
    pay_goEmerchant($paytot);
  } elsif (defined $authNname) {
    pay_authorizeNet($paytot);
  } elsif (defined $linkPconfig) {
    pay_linkPoint($paytot);
  } elsif (defined $cpstnID) {
    pay_capstone($paytot);
  } elsif (defined $paygeaAccount) {
    pay_paygea_NEWAPI($paytot);
  } elsif (defined $plugandpay) {
        pay_plugnpay($paytot);
  } elsif (defined $paygateid) {
        pay_paygate($paytot);
  } elsif (defined $firePayNum) {
  pay_firepay($paytot);
  } else {
    # this should never happen with the Gizmo card....
    $error = "We are experiencing problems with the checkout system.  This store is still unable to process orders.  We will be back up soon..";
    Main();
    exit;
  }
}

sub Add {
  my $paytot = shift;
  if ($OrderType eq 'Cam_Order'){
  #CAMBILL
  # Get the aes value from the db w/a select. Then use the val for the INSERT.
  my $enc_val_cc = Encrypt($credit_card, $ccEncryptString);
    
  $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
    my $sqlstatement = "update CamAuth set Total = (Total + $paytot) where  cc = " . esc($enc_val_cc);
     $dbhS->do($sqlstatement);
  $dbhS->disconnect();
  #CAMBILL
  }

  my $sth;
  if (!$customer_id) {
    # not sure if this can ever happen, but just in case:
    $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
    $sth = $dbhS->prepare("select CustomerID from ConsumerOrderAddress where
      Email = '" . esc($q->param('Email')) . "' and
      FullName = '" . esc($q->param('First_Name')) . "' limit 1
      ") if $pay_method eq 'CC';
    $sth = $dbhS->prepare("select CustomerID from ConsumerOrderAddress where
      Email = '" . esc($q->param('gizmo_email')) . "' and
      FullName = '" . esc($q->param('gizmo_username')) . "' limit 1
      ") if $pay_method eq 'GizmoCard';
    $sth = $dbhS->prepare("select CustomerID from ConsumerOrderAddress where
        Email = '" . esc($q->param('clipcash_email')) . "' and
        FullName = '" . esc($q->param('clipcash_account')) . "' limit 1
       ") if $pay_method eq 'ClipCash';
      
    if (!defined($sth) || !$sth->execute()) {print "\n(select from cust) STH: " . $dbh->errstr . "<br>\n"; die;}
    if ($sth->rows) {
      while (my $row_ref = $sth->fetchrow_hashref()) {
        $customer_id = $row_ref->{'CustomerID'};
      }
    } else {
      $customer_id = time . $ENV{'REMOTE_ADDR'};
      $customer_id =~ s/\D+//g;
    }
  }
  my $cust_name;
  $cust_name = $q->param('Full_Name') if $pay_method eq 'CC';
  $cust_name = $q->param('First_Name') . ' ' . $q->param('Last_Name') if defined $authNname;
  $cust_name = $q->param('gizmo_username') if $pay_method eq 'GizmoCard';
  $cust_name = $q->param('clipcash_name') if $pay_method eq 'ClipCash';
  my $email;
  $email     = $q->param('Email') if $pay_method eq 'CC';
  $email     = $q->param('gizmo_email') if $pay_method eq 'GizmoCard';
  $email     = $q->param('clipcash_email') if $pay_method eq 'ClipCash';

  my $mysql_insert;
  $mysql_insert = "replace into Customers SET ID = '" . $customer_id . "', FullName = '" . esc($cust_name) . "', Email = ''";
  if ($pay_method eq 'CC') {
   if ($q->param('CheckOut') eq 'Order Videos'){  
      $mysql_insert .= ", AddressOne = '" . esc($q->param('Address_1')) . "', AddressTwo = '" . esc($q->param('Address_2')) . "', City = '" . esc($q->param('City')) . "', State = '" . esc($q->param('State')) . "', ZipCode = '" . esc($q->param('Zip_Code')) . "', Country = '" . esc($q->param('Country')) . "', CreditCardNumber = ' ', ExpireMonth = ' ', ExpireYear = ' ', proxyScore = ' ', spamScore = ' ', Score = ' '"; 
   } else {
  $mysql_insert .= ", AddressOne = ' ', AddressTwo = ' ', City = '" . esc($q->param('City')) . "', State = '" . esc($q->param('State')) . "', ZipCode = ' ', Country = ' ', CreditCardNumber = ' ', ExpireMonth = ' ', ExpireYear = ' ', proxyScore = ' ', spamScore = ' ', Score = ' '";
   }
  }

  $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
  $sth = $dbh->prepare($mysql_insert);
  #$dbh->do('lock tables Customers write');
  if (!defined($sth) || !$sth->execute()) {print "\n(insert cust) STH: " . $dbh->errstr . "<br>SQL: $mysql_insert<br>\n"; die;}
  #$dbh->do('unlock tables');
  $sth->finish;

  $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
  $sth = $dbh->prepare("select * from StoreProducers where ID = '" . esc($q->param('storeid')) . "'");
  if (!defined($sth) || !$sth->execute()) {print "\n(select storeprod) STH: " . $dbh->errstr . "<br>\n"; die;}
  #CAMBILL VARIANT
  my ($cc_clippercentage, $giz_clippercentage, $videopercentage, $giz_videopercentage, $cc_imagepercentage, $giz_imagepercentage, $pemail, $cc_campercentage, $giz_campercentage);
  while (my $row_ref = $sth->fetchrow_hashref()) {
    $cc_clippercentage   = $row_ref->{'ClipP'};
    $giz_clippercentage  = $row_ref->{'GizmoP'};
    $videopercentage     = $row_ref->{'VideoP'};
    $giz_videopercentage = $row_ref->{'GizmoVideoP'};
    $cc_imagepercentage  = $row_ref->{'ImageP'};
    $giz_imagepercentage = $row_ref->{'GizmoImageP'};
    $pemail              = $row_ref->{'Email'};
    $cc_campercentage    = $row_ref->{'CamP'};
    $giz_campercentage   = $row_ref->{'GizmoCamP'};
  }
  $sth->finish;

  my $totalamount = sprintf("%.2f", $paytot);
  my $merchantamount = sprintf("%.2f", $totalamount * .04);
  my $pcamount = 0;
  my $vendorcommission;

  # order is crucial here
  $vendorcommission = sprintf("%.2f", $totalamount * ('.' . $cc_clippercentage));
  $vendorcommission = sprintf("%.2f", $totalamount * ('.' . $videopercentage))     if $q->param('CheckOut') eq 'Order Videos';
  $vendorcommission = sprintf("%.2f", $totalamount * ('.' . $cc_imagepercentage))  if $q->param('CheckOut') eq 'Order Pixxx';
  $vendorcommission = sprintf("%.2f", $totalamount * ('.' . $cc_campercentage))  if $q->param('CheckOut') eq 'Cam_Order';

  $vendorcommission = sprintf("%.2f", $totalamount * ('.' . $giz_clippercentage))  if $pay_method eq 'GizmoCard';
  $vendorcommission = sprintf("%.2f", $totalamount * ('.' . $giz_videopercentage)) if $q->param('CheckOut') eq 'Order Videos' and $pay_method eq 'GizmoCard';
  $vendorcommission = sprintf("%.2f", $totalamount * ('.' . $giz_imagepercentage)) if $q->param('CheckOut') eq 'Order Pixxx'  and $pay_method eq 'GizmoCard';
  $vendorcommission = sprintf("%.2f", $totalamount * ('.' . $giz_campercentage)) if $q->param('CheckOut') eq 'Cam_Order'  and $pay_method eq 'GizmoCard';

  $vendorcommission = sprintf("%.2f", $totalamount * ('.' . $giz_clippercentage))  if $pay_method eq 'ClipCash';
  $vendorcommission = sprintf("%.2f", $totalamount * ('.' . $giz_videopercentage)) if $q->param('CheckOut') eq 'Order Videos' and $pay_method eq 'ClipCash';
  $vendorcommission = sprintf("%.2f", $totalamount * ('.' . $giz_imagepercentage)) if $q->param('CheckOut') eq 'Order Pixxx'  and $pay_method eq 'ClipCash';
  $vendorcommission = sprintf("%.2f", $totalamount * ('.' . $giz_campercentage)) if $q->param('CheckOut') eq 'Cam_Order'  and $pay_method eq 'ClipCash';
  
      
  my $netamount = sprintf("%.2f", $totalamount - $merchantamount - $vendorcommission - $pcamount);
  $cc = 99 if $pay_method eq 'GizmoCard';
  $cc = 97 if $pay_method eq 'ClipCash';
  my $service = 'PClipOrder';
  $service = 'P Video Order' if $q->param('CheckOut') eq 'Order Videos';
  $service = 'P Image Order' if $q->param('CheckOut') eq 'Order Pixxx';
  $service = 'P Cam Order' if $q->param('CheckOut') eq 'Cam_Order';
  
  $mysql_insert = "
  insert into Transactions set
  CustomerID      = '$customer_id',
  Service         = '$service',
  TotalAmount     = '$totalamount',
  MerchantAmount  = '$merchantamount',
  VendorComission = '$vendorcommission',
  NetAmount       = '$netamount',
  cc              = '$cc'
  ";
  $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
  $sth = $dbh->prepare($mysql_insert);
  #$dbh->do('lock tables Transactions write');
  if (!defined($sth) || !$sth->execute()) {print "\n(insert transactions) STH: " . $dbh->errstr . "<br>\n"; die;}
  #$dbh->do('unlock tables');
  $sth->finish;

  $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
  $sth = $dbh->prepare("select last_insert_id()");
  if (!defined($sth) || !$sth->execute()) {print "\n(get last trans id) STH: " . $dbh->errstr . "<br>\n"; die;}
  my $sorder = $sth->fetch->[0];
  $sth->finish;
  #$cust_name =~ s/'/'';
  
  # Get the aes value from the db w/a select. Then use the val for the INSERT.
  my $enc_val_cc = Encrypt($credit_card, $ccEncryptString);
  my $enc_val_full_name = Encrypt($cust_name, $nameEncryptString);  
  my $enc_val_email = Encrypt($email, $emailEncryptString);   
    
  my $secure_sql = "insert into ConsumerOrder set
  SONumber = '$sorder',
  Credit_Card = '" . esc($enc_val_cc) . "',
  Name = '" . esc($enc_val_full_name) . "',
  Email = '" . esc($enc_val_email) . "',
  IPAddress = inet_aton('$remote_addr'),
  Order_Date = NOW(),
  ProducerID = '" . $q->param('storeid') . "',
  CustomerID = '$customer_id',
  TotalAmount = '$totalamount',
  Service = '$service'";
#$OrderType'";


  $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
  $sth = $dbhS->prepare($secure_sql);
  if (!defined($sth) || !$sth->execute()) {print "\n(Create Consumer Order entry error) ERROR.  <br>\n"; die;}
  $sth->finish;
 
  #Store FIRST First first Four and Last four.
  my $FirstFour = substr($credit_card, 0, 4);
  my $LastFour = substr($credit_card, 12, 4);
  my ($CustFirst, $CustLast, @ExtraneousNames) = split(/ /,$cust_name);
  $CustFirst = substr($CustFirst, 0, 1);
  $CustLast = substr($CustLast, 0, 1);
  $FirstFour =~ s/[^0-9]//g;
  $LastFour =~ s/[^0-9]//g;
  my $LastFourLen = length($LastFour);
  if ($LastFourLen < 4) { $LastFour = "0" . $LastFour;}
  my $secure_sql = "
  Insert into First_Last_Four set
  SONumber = '$sorder',
  First = '$FirstFour',
  Last = '$LastFour',
  FNFL = '$CustFirst',
  LNFL = '$CustLast',
  DTTM = NOW()";
  #UCOMMENT TOMORROW!!  CHAGEN
  $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
  $sth = $dbhS->prepare($secure_sql);
  if (!defined($sth) || !$sth->execute()) {print "\n(Create First Last Four entry error) ERROR.  <br>\n"; die;}
  $sth->finish;

  # Write to ConsumerOrderAddress
  $secure_sql = "insert into ConsumerOrderAddress SET SONumber = $sorder, CustomerID = '$customer_id', FullName = '" . esc($cust_name) . "', Email = '" . esc($email) . "'";
  if ($pay_method eq 'CC') {
    my $enc_exp_month = Encrypt($q->param('Expiration_Month_Card'), $ccEncryptString);
    my $enc_exp_year = Encrypt($q->param('Expiration_Year'), $ccEncryptString);   
    $secure_sql .= ", AddressOne = '" . esc($q->param('Address_1')) . "', AddressTwo = '" . esc($q->param('Address_2')) . "', City = '" . esc($q->param('City')) . "', State = '" . esc($q->param('State')) . "', ZipCode = '" . esc($q->param('Zip_Code')) . "', Country = '" . esc($q->param('Country')) . "', ExpireMonth = '" . esc($enc_exp_month) . "', ExpireYear = '" . esc($enc_exp_year) . "'";
  }
  $sth = $dbhS->prepare($secure_sql);
  if (!defined($sth) || !$sth->execute()) {print "\n(Create Consumer Order entry error) <br>\n"; die;}
  $sth->finish;

  $dbhS->disconnect();

 


  $sth = $dbh->prepare("insert into TrackOrder set SONumber = $sorder, OrderIP = '$remote_addr', OrderDTTM = NOW(), OrderCountry = '$remote_country', Allowed = 0");
  if (!defined($sth) || !$sth->execute()) {print "\nTrack Order STH: Insert into TrackOrder Failed <br>\n"; die;}
  $sth->finish;
  my $z = 1;
  

  #FIX ORDER REFERRAL
  #my $Treferrer = substr($referrer,0, 253);
  #my $TCampaignCode = substr($CampaignCode, 0, 11);
  #$sth = $dbh->prepare("insert into OrderReferral values($sorder, '$Treferrer',NOW(),'$TCampaignCode')");
  #if (!defined($sth) || !$sth->execute()) {print "\nOrder Referrer STH: Insert into OrderReferral Failed <br>\n"; die;}
  #$sth->finish;
  
  my ($customer_email, $vendor_email, $vendor_pack_email, $admin_email, $tneilmon);
  my %oldid;
  my %vidformats;
  my $shipping = 0;
  my $pass;
  $pass = $credit_card . "-" . $q->param('Expiration_Month_Card') . "-" . $q->param('Expiration_Year') if $pay_method eq 'CC';
  $pass = 'GizmoCard User: ' . $q->param('gizmo_username') if $pay_method eq 'GizmoCard';
  $pass = 'Clipcash: ' . $q->param('clipcash_number') if $pay_method eq 'ClipCash';
#qqq
  
  foreach my $id (sort @id) {
    chomp $id;
    my $vtype;
    ($id, $vtype) = split /:/, $id;
    next if $oldid{$id};
    $oldid{$id}++;
    $vidformat = $vtype;
    $vidformats{$vtype}++;

    my $filename = '';
    my $file_insert = '';
    my $mysql_select;

    for ($q->param('CheckOut')) {
      /Order Videos/ && do {
        $mysql_select = "select * from StoreProducerVideos where VideoID = '$id' and ProducerID = '" . $q->param('storeid') . "' limit 1";
        last;
      };
      /Order Pixxx/  && do {
        $mysql_select = "select * from StoreProducerImages where ImageID = '$id' and ProducerID = '" . $q->param('storeid') . "' limit 1";
        last;
      };
      $mysql_select = "select * from StoreProducerClips  where ClipID = '$id'  and ProducerID = '" . $q->param('storeid') . "' limit 1";
    }

    $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
    $sth = $dbh->prepare($mysql_select);
    if (!defined($sth) || !$sth->execute()) {print "\n(get from clips) STH: " . $dbh->errstr; die;}
    my ($ititle, $vendor_ititle, $iprice, $pcommission);
    my $st = 'Clip';
    $st = 'Video' if $q->param('CheckOut') eq 'Order Videos';
    $st = 'Image' if $q->param('CheckOut') eq 'Order Pixxx';
    while (my $row_ref = $sth->fetchrow_hashref()) {
      $ititle = $vendor_ititle = $row_ref->{"${st}Title"};
      for ($q->param('CheckOut')) {
        /Order Videos/ && do {
          $ititle .= " - $vtype Format";
          last;
        };
        /Order Pixxx/  && do {
          $filename = $row_ref->{"${st}_Zip_Name"};
          last;
        };
        $filename = $row_ref->{"${st}Name"};
      }
      $iprice = $row_ref->{"${st}Price"};

      # order is crucial here
      $pcommission = $iprice * ('.' . $cc_clippercentage);
      $pcommission = $iprice * ('.' . $videopercentage)     if $q->param('CheckOut') eq 'Order Videos';
      $pcommission = $iprice * ('.' . $cc_imagepercentage)  if $q->param('CheckOut') eq 'Order Pixxx';

      $pcommission = $iprice * ('.' . $giz_clippercentage)  if $pay_method eq 'GizmoCard';
      $pcommission = $iprice * ('.' . $giz_videopercentage) if $q->param('CheckOut') eq 'Order Videos' and $pay_method eq 'GizmoCard';
      $pcommission = $iprice * ('.' . $giz_imagepercentage) if $q->param('CheckOut') eq 'Order Pixxx'  and $pay_method eq 'GizmoCard';
      
      $pcommission = $iprice * ('.' . $giz_clippercentage)  if $pay_method eq 'ClipCash';
      $pcommission = $iprice * ('.' . $giz_videopercentage) if $q->param('CheckOut') eq 'Order Videos' and $pay_method eq 'ClipCash';
      $pcommission = $iprice * ('.' . $giz_imagepercentage) if $q->param('CheckOut') eq 'Order Pixxx'  and $pay_method eq 'ClipCash';


    }
    if ($q->param('CheckOut') eq 'Cam_Order') {
        $iprice = $camPrice;
        $pcommission = $iprice * ('.' . $cc_campercentage);
        $pcommission = $iprice * ('.' . $giz_campercentage)  if $pay_method eq 'GizmoCard';
        $pcommission = $iprice * ('.' . $giz_campercentage)  if $pay_method eq 'PureVanilla';
        if ($camType == 2){ 
    $ititle = $camUserName . " Membership Order";
        }
        else {
            $ititle = $camUserName . " Cam Show";
        }
    }

    $sth->finish;
    $file_insert = $rande . $z++ . ".zip" unless $q->param('CheckOut') eq 'Order Videos';
#qqq
    # Do for Videos
    if ($q->param('CheckOut') eq 'Order Videos') {
      my $st = 'Video';
      $mysql_insert = "
      insert into Producer${st}Members set
      ProducerID = '" . esc($q->param('storeid')) . "',
      CustomerID = '$customer_id',
      SONumber   = '$sorder',
      DatePaid   = NOW(),
      ${st}ID    = '" . esc($log_in) . "',
      Pass       = '" . $customer_id . "',
      Active     = '1'
      ";
      $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
      $sth = $dbh->prepare($mysql_insert);
      #$dbh->do("lock tables Producer${st}Members write");
      if (!defined($sth) || !$sth->execute()) {print "\n(insert $st members) STH: " . $dbh->errstr . "\n"; die;}
      #$dbh->do('unlock tables');
      $sth->finish;
    }
   # Do for Cams CAMBILL
    elsif ($q->param('CheckOut') eq 'Cam_Order') {
      my $st = 'Cam';
      $mysql_insert = "
      insert into Producer${st}Members set
      ProducerID = '" . esc($storeid) . "',
      CustomerID = '$customer_id',
      SONumber   = '$sorder',
      DatePaid   = NOW(),
      ${st}ID    = '" . esc($log_in) . "',
      Pass       = '" . esc($customer_id) . "',
      Active     = '1',
      CamTrans   = '$transID'
      ";
      $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
      $sth = $dbh->prepare($mysql_insert);
      #$dbh->do("lock tables Producer${st}Members write");
      if (!defined($sth) || !$sth->execute()) {print "\n(insert $st members) STH: $mysql_insert" . $dbh->errstr . "\n"; die;}
      #$dbh->do('unlock tables');
      $sth->finish;
    }


    # Do for Clips & Images
    else {
      my $st = 'Clip';
      $st = 'Image' if $q->param('CheckOut') eq 'Order Pixxx';
      $mysql_insert = "
      insert into Producer${st}Members set
      ProducerID    = '" . esc($q->param('storeid')) . "',
      CustomerID    = '$customer_id',
      SONumber      = '$sorder',
      Expires       = date_add(NOW(), interval 2 day),
      DatePaid      = NOW(),
      ${st}FileName = '" . esc($file_insert) . "',
      OrigFileName  = '" . esc($filename) . "',
      ${st}ID       = '" . esc($log_in) . "',
      Pass          = '" . $customer_id . "',
      Active        = '1'
      ";
      $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
      $sth = $dbh->prepare($mysql_insert);
      #$dbh->do("lock tables Producer${st}Members write");
      if (!defined($sth) || !$sth->execute()) {print "\n(insert $st members) STH: " . $dbh->errstr . "\n"; die;}
      #$dbh->do('unlock tables');
      $sth->finish;
    }

    # do for clips & videos & images
    $mysql_insert = "
    insert into ProducerDetails set
    CustomerID = '" . $customer_id . "',
    Title = '" . esc($ititle) . "',
    Price = '$iprice',
    TransDate = NOW(),
    ProducerID = '" . esc($q->param('storeid')) . "',
    ProducerCommission = '$pcommission',
    TransID = '$sorder',
    TrackNum = '$customer_id-$sorder',
    VidFormat = '$vidformat',
    g = '$gizmo_g',
    ";
    if ($q->param('CheckOut') eq 'Order Videos') {
      $mysql_insert .= "VideoID = '$id'";
    } elsif ($q->param('CheckOut') eq 'Order Pixxx') {
      $mysql_insert .= "ImageID = '$id'";
    } else {
      $mysql_insert .= "ClipID = '$id'";
    }
    $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
    $sth = $dbh->prepare($mysql_insert);
    #$dbh->do('lock tables ProducerDetails write');
    if (!defined($sth) || !$sth->execute()) {print "\n(insert prod details) STH: " . $dbh->errstr . "\n"; die;}
    #$dbh->do('unlock tables');
    $sth->finish;

    my $neilsmoney = sprintf("%.2f", $iprice - $pcommission);
    $tneilmon += $neilsmoney;
    $admin_email .= "<tr><td>" . $ititle . "</td><td>\$" . $iprice . "</td><td>\$" . $pcommission . "</td><td>" . $neilsmoney . "</td></tr>\n";
    $vendor_email .= "<tr><td>" . $ititle . "</td><td>\$" . $iprice . "</td><td>\$" . $pcommission . "</td></tr>\n";
    $vendor_pack_email .= "<tr><td>$vtype</td><td>" . $vendor_ititle . "</td><td>\$" . $iprice . "</td></tr>\n" if $q->param('CheckOut') eq 'Order Videos';
    $customer_email .= $ititle . "\n";
  }

  # do for videos
  if ($q->param('CheckOut') eq 'Order Videos') {
    if (defined $ctry_ship{$q->param('Country')}) {
      $shipping = $ctry_ship{$q->param('Country')};
    } else {
      $shipping = $ctry_ship{'default'};
    }
    if ($shipping > 0) {
      my $pcommission = $shipping * ('.' . $videopercentage);
      $pcommission = $shipping * ('.' . $giz_videopercentage) if $pay_method eq 'GizmoCard';
      $pcommission = $shipping * ('.' . $giz_videopercentage) if $pay_method eq 'ClipCash';
      $mysql_insert = "
      insert into ProducerDetails set
      CustomerID = '" . $customer_id . "',
      Title = 'Shipping',
      Price = $shipping,
      TransDate = NOW(),
      ProducerID = '" . esc($q->param('storeid')) . "',
      ProducerCommission = '$pcommission',
      TransID = '$sorder',
      TrackNum = '$customer_id-$sorder',
      VideoID = '1'
      ";
      $sth = $dbh->prepare($mysql_insert);
      #$dbh->do('lock tables ProducerDetails write');
      if (!defined($sth) || !$sth->execute()) {print "\nSTH: " . $dbh->errstr . "\n"; die;}
      #$dbh->do('unlock tables');
      $sth->finish;
    }
  }

  my $opted_out = 0;
  my $this_pid_found = 0;
  $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
  $sth = $dbh->prepare("select Email, PID, Active from ProducerEmail where Email = '" . esc($q->param('Email')) . "'");
  if (!defined($sth) || !$sth->execute()) {print "\n(select email) STH: " . $dbh->errstr . "<br>\n"; die;}
  while (my $row_ref = $sth->fetchrow_hashref()) {
    $this_pid_found = 1 if $row_ref->{'PID'}    == $q->param('storeid');
    $opted_out      = 1 if $row_ref->{'Active'} == 0;
  }
  if ((!($opted_out and $this_pid_found)) && $optin) {
    $mysql_insert = "replace into ProducerEmail set
    PID = '" . esc($q->param('storeid')) . "',
    Email = '" . esc($q->param('Email')) . "'
    ";
    $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
    #$dbh->do('lock tables ProducerEmail write');
    $sth = $dbh->prepare($mysql_insert);
    #$dbh->do('unlock tables');
    if (!defined($sth) || !$sth->execute()) {print "\n(insert prod email) STH: " . $dbh->errstr . "\n"; die;}
    $sth->finish;
  }
  $sth->finish;

  if ($q->param('Session')) {
    $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
    $sth = $dbh->prepare("replace into Session set ID = '" . esc($q->param('Session')) . "', Store = '3'");
    #$dbh->do('lock tables Session write');
    if (!defined($sth) || !$sth->execute()) {print "\n(insert session) STH: " . $dbh->errstr; die;}
    #$dbh->do('unlock tables');
  }

  my $fullname = $cust_name;
  $fullname = "Gizmo Card Account" . $q->param('gizmo_username') if $pay_method eq 'GizmoCard';
  $fullname = "Clip Cash Account" . $q->param('clipcash_name') if $pay_method eq 'ClipCash';
  # my $email = $q->param('Email'); # $email already set
  my $address = $q->param('Address_1') || '';
  if ($q->param('Address_2')) {$address .= "\n" . $q->param('Address_2');}
  my $city = $q->param('City') || '';
  my $state = $q->param('State') || '';
  my $zipcode = $q->param('Zip_Code') || '';
  my $country = $countries_rev{$q->param('Country')} || '';
  my $grand_total = $paytot;
  my $pay_meth_text;
  $pay_meth_text = "Your credit card was billed \$$grand_total from $descriptor." if $pay_method eq 'CC';
  $pay_meth_text = "Your Gizmo Card account was debited \$$grand_total." if $pay_method eq 'GizmoCard';
  $pay_meth_text = "Your Clip Cash Card account was debited \$$grand_total." if $pay_method eq 'ClipCash';

  my $ccfs_html = $maxmind_ccfs_info;
  $ccfs_html =~ s/\n/<br>/g;
  $ccfs_html =~ s/=>/: /g;

  for ($q->param('CheckOut')) {
    /Order Videos/ && do {
      my $vidformats = 'Format';
      $vidformats .= 's' if scalar(keys %vidformats) > 1;
      $vidformats .= ': ';
      foreach my $key (sort keys %vidformats) {
        $vidformats .= ' ' . $key . ',';
      }
      chop $vidformats;

      # html
      print get_video_html($fullname, $descriptor, $grand_total, $pemail, $log_in, $sorder, $customer_email);

      # Customer
      $mailer->open({Subject => 'Video Order', To => $email, From => 'info@videos4sale.com', });
      print $mailer &get_cust_vid_email($fullname, $log_in, $sorder, $grand_total, $descriptor, $customer_email, $pemail, $address, $city, $state, $zipcode, $country, $vidformats);
      $mailer->close;

      # Producer
      $mailer->open({Subject => 'VIDEO ORDER', To => $pemail, From => 'videos4sale@clips4sale.com', 'Content-Type' => 'text/html' });
      print $mailer &get_prod_vid_email($storeid, $sorder, $vendor_email, $shipping, $totalamount, $vendorcommission, $customer_id, $log_in, $fullname, $email, $address, $city, $state, $zipcode, $country, $ccfs_html, $vidformats);
      $mailer->close;

      # Producer Packing List
      $mailer->open({Subject => 'VIDEO ORDER PACKING LIST', To => $pemail, From => 'videos4sale@clips4sale.com', 'Content-Type' => 'text/html' });
      print $mailer &get_prod_pack_email($storeid, $sorder, $vendor_pack_email, $shipping, $totalamount, $customer_id, $log_in, $fullname, $email, $address, $city, $state, $zipcode, $country, $vidformats);
      $mailer->close;

      # Neil
      my $subj = 'PRODUCER VIDEO ORDER';
      $subj .= ' LARGE ORDER ' if $totalamount > 75;
      $mailer->open({Subject => 'PRODUCER VIDEO ORDER', To => 'orders@intermarkproductions.com', From => 'info@videos4sale.com', 'Content-Type' => 'text/html' });
      print $mailer &get_neil_vid_email($storeid, $sorder, $admin_email, $shipping, $totalamount, $vendorcommission, $tneilmon, $customer_id, $log_in, $email, $credit_card, $remote_addr, $fullname, $address, $city, $state, $zipcode, $country, $ccfs_html, $vidformats);
      $mailer->close;

      last;
    };

/Cam_Order/ && do {
      #print "<br><br><br><h1>I have processed a cam order!  : $transID :<br><br><Br></h1>";
$csth = $camDB->prepare("update payments set status = '1', email = '" . $q->param('Email'). "', buyer = '".$q->param('Full_Name')."' where id= $transID");
      if (!defined ($csth) || !$csth->execute()){die "The payment update for the cam purchase failed";}
      # Neil
      my $subj = '';
      if ($camType == 2) {
        $subj = 'PRODUCER MEMBER ORDER';      }
      else {
        $subj = 'PRODUCER CAM ORDER';
      }
      $subj .= ' LARGE ORDER ' if $totalamount > 100;
      $mailer->open({Subject => $subj, To => 'admin@intermarkproductions.com', Cc => 'info@clips4sale.com', Cc => 'orders@clips4sale.com',  From => 'info@c4slive.com', 'Content-Type' => 'text/html' });
      print $mailer "Cam/Member order processed";
      print $mailer &get_neil_cam_email($storeid, $sorder, $admin_email, $totalamount, $vendorcommission, $tneilmon, $descriptor, $customer_id, $log_in, $email, $pass, $remote_addr, $remote_country, $fullname, $address, $city, $state, $zipcode, $country, $ccfs_html,$transID);
          $mailer->close;      #($storeid, $sorder, $admin_email, $shipping, $totalamount, $vendorcommission, $tneilmon, $customer_id, $log_in, $email, $credit_card, $remote_addr, $fullname, $address, $city, $state, $zipcode, $country, $ccfs_html, $vidformats);
      $mailer->close;
      my $CAMURL = 'http://' . $camUserName . '.c4slive.com/process.php?verify=' . $camVerify;

print $q->redirect($CAMURL);
        last;
     };

    /Order Pixxx/ && do {
      # html
      print get_image_html($fullname, $log_in, $the_domain, $pay_meth_text, $sorder);

      # Customer
      $mailer->open({ Subject => $gizmo_sub . ' Pixxx Order', To => $email, From => 'info@' . $the_domain });
      print $mailer &get_cust_image_email($fullname, $log_in, $sorder, $pay_meth_text, $customer_email, $the_domain, $pemail, $address, $city, $state, $zipcode, $country);
      $mailer->close;

      # Producer
      $mailer->open({ Subject => $gizmo_sub . ' PIXXX ORDER', To => $pemail, From => 'orders@clips4sale.com', 'Content-Type' => 'text/html' });
      print $mailer &get_prod_image_email($storeid, $sorder, $log_in, $vendor_email, $totalamount, $vendorcommission, $remote_addr, $remote_country, $customer_id, $fullname, $email, $city, $state, $country, $ccfs_html);
      $mailer->close;

      # Neil
      my $subj = $gizmo_sub . ' PRODUCER PIXXX ORDER';
      $subj .= ' (Gizmo Card)' if $pay_method eq 'GizmoCard';
      $subj .= ' (Clip Cash)' if $pay_method eq 'ClipCash';
      $subj .= ' LARGE ORDER ' if $totalamount > 75;
      $mailer->open({ Subject => $subj, To => 'orders@intermarkproductions.com', From => 'info@' . $the_domain, 'Content-Type' => 'text/html' });
      print $mailer &get_neil_image_email($storeid, $sorder, $admin_email, $totalamount, $vendorcommission, $tneilmon, $descriptor, $customer_id, $log_in, $email, $pass, $remote_addr, $remote_country, $fullname, $address, $city, $state, $zipcode, $country, $ccfs_html);
      $mailer->close;
      last;
    };

    # if none of above, then is clip order
    # html
    print get_clip_html($fullname, $log_in, $the_domain, $pay_meth_text, $sorder);

    # Customer
    $mailer->open({ Subject => $gizmo_sub . ' Clip Order', To => $email, From => 'info@' . $the_domain });
    print $mailer &get_cust_clip_email($fullname, $log_in, $sorder, $pay_meth_text, $customer_email, $the_domain, $pemail, $address, $city, $state, $zipcode, $country);
    $mailer->close;

    # Producer
    my $subj = $gizmo_sub . ' CLIP ORDER';
       $subj .= ' (Gizmo Card)' if $pay_method eq 'GizmoCard';
       $subj .= ' (Clip Cash Card)' if $pay_method eq 'ClipCash';
                      
    $mailer->open({ Subject => $subj, To => $pemail, From => 'orders@clips4sale.com', 'Content-Type' => 'text/html' });
    print $mailer &get_prod_clip_email($storeid, $sorder, $log_in, $vendor_email, $totalamount, $vendorcommission, $remote_addr, $remote_country, $customer_id, $fullname, $email, $city, $state, $country, $ccfs_html);
    $mailer->close;

    # Neil
    $subj = $gizmo_sub . ' PRODUCER CLIP ORDER';
    $subj .= ' (Gizmo Card)' if $pay_method eq 'GizmoCard';
    $subj .= ' (Clip Cash Card)' if $pay_method eq 'ClipCash';
    $subj .= ' LARGE ORDER ' if $totalamount > 75;
    $mailer->open({ Subject => $subj, To => 'orders@intermarkproductions.com', From => 'info@' . $the_domain, 'Content-Type' => 'text/html' });
    print $mailer &get_neil_clip_email($storeid, $sorder, $admin_email, $totalamount, $vendorcommission, $tneilmon, $descriptor, $customer_id, $log_in, $email, $pass, $remote_addr, $remote_country, $fullname, $address, $city, $state, $zipcode, $country, $ccfs_html);
    $mailer->close;
    #Lets see how many orders you made
  }
        CheckNumOrders($remote_addr, $cust_name, $sorder);

                        #insert into the Order_MaxMind table
    my $MaxSQL = "insert into Order_MaxMind 
                        set SONumber = $sorder,
                        ProducerID = " . $q->param('storeid') . ",
                        IPAddress = inet_aton('$remote_addr'),
                        Max_AnonymousProxy = '$anonymousProxy',
      Max_City = '$MaxCity',
      Max_State = '$MaxState',
                        Max_Country = '$MaxCountry',
                        Max_Distance = '$MaxDistance',
                        Max_HighRiskCountry = '$MaxHighRisk',
                        Max_IP_Region = '$MaxIPRegion',
                        Max_MaxMindID = '$MaxID',
                        Max_ProxyScore = $proxyScore,
                        Max_Score = $score,
      Max_SpamScore = '$MaxSpamScore',
                        Max_IP_ISP = '$MaxISP',
                        Max_IP_ORG = '$MaxORG',
                        MaxMindDetails = '$maxmind_ccfs_info',
      TransactionDateTime = NOW(),
      Service = '$service'";
    # open (OUTPUT, '>>/tmp/MaxMind');
  # print OUTPUT "$MaxSQL\n\n\n\n\n\n"; 
      #write all credit card transactions to the Order_MaxMind table.
      if ($pay_method ne 'ClipCash' and $pay_method ne 'GizmoCard') {
        $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
          $sth = $dbhS->prepare($MaxSQL);
          if (!defined($sth) || !$sth->execute()) {print "\n(Create Consumer Order entry error) " . $dbhS->errstr. " <br>\n"; die;}
          $sth->finish;
        $dbhS->disconnect();
      }


    
    #CHAGEN Clear out the Stores page in order to generate for sales
    my $requrl = "clips4sale.com/work/store/index.php?storeid=$storeid&DeleteSiteStatic=1";
    my $run = `/usr/bin/lwp-request "http://www15.$requrl"`;
    $run = `/usr/bin/lwp-request "http://www150.$requrl"`;
    $run = `/usr/bin/lwp-request "http://www151.$requrl"`;
    sleep(1);
    $run = `/usr/bin/lwp-request "http://www15.$requrl"`;
    $run = `/usr/bin/lwp-request "http://www16.$requrl"`;
    $run = `/usr/bin/lwp-request "http://www20.$requrl"`;
    $run = `/usr/bin/lwp-request "http://www21.$requrl"`;
    sleep(1);
    $run = `/usr/bin/lwp-request "http://www22.$requrl"`;
    $run = `/usr/bin/lwp-request "http://www152.$requrl"`;

  #Integrate NATS Nats nats    
  if ($CampaignCode ne '') {
          my $run2 = `/usr/bin/lwp-request "https://nats.clips4sale.com/customcode/natshook.php?natscode=$CampaignCode&so=$sorder&amount=0&nats_store_id=CLIPS4SALE&transtype=sale"`;
        }
  
}

sub CheckNumOrders {#  Send out Info on Multiple Order
    my $remote_addr = shift;
    my $cust_name = shift;
    my $sorder = shift;
    my $NameCount = 0;
    my $EmailCount = 0;
    my $IPCount = 0;
    my $ccCount = 0;
  
 
    #Lets Gather Some Data
    my $name_sql = "select count(*) as c1 from ConsumerOrder where Order_Date > now() - interval 24 hour and  Name = aes_encrypt('" . esc($cust_name) . "', '$nameEncryptString')";
    my $ip_sql = "select count(*) as c1 from ConsumerOrder where Order_Date > now() - interval 24 hour and  IPAddress = inet_aton('$remote_addr')";
    my $cc_sql = "select count(*) as c1 from ConsumerOrder where Order_Date > now() - interval 24 hour and Credit_Card = aes_encrypt('$credit_card', '$ccEncryptString')";
    my $email_sql = "select count(*) as c1 from ConsumerOrder where Order_Date > now() - interval 24 hour and Email = aes_encrypt('" . esc($q->param('Email')) . "', '$emailEncryptString')";


    $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd); 
    
    $sth = $dbhS->prepare($name_sql); 
    if (!defined($sth) || !$sth->execute()) {print "\n(Get Name Count)"; die;} 
    while (my $row_ref = $sth->fetchrow_hashref()) {
             $NameCount = $row_ref->{"c1"};
    }
    $sth->finish();
    $sth = $dbhS->prepare($email_sql); 
    if (!defined($sth) || !$sth->execute()) {print "\n(Get Email Count) STH: "; die;} 
    while (my $row_ref = $sth->fetchrow_hashref()) {
             $EmailCount = $row_ref->{"c1"};
    }
    $sth->finish();
    $sth = $dbhS->prepare($ip_sql); 
    if (!defined($sth) || !$sth->execute()) {print "\n(Get IP Count) "; die;} 
    while (my $row_ref = $sth->fetchrow_hashref()) {
             $IPCount = $row_ref->{"c1"};
    }
    $sth->finish();
    $sth = $dbhS->prepare($cc_sql); 
    if (!defined($sth) || !$sth->execute()) {print "\n(Get CC Count) "; die;} 
    while (my $row_ref = $sth->fetchrow_hashref()) {
             $ccCount = $row_ref->{"c1"};
    }
    $sth->finish();

  if ($NameCount >= 3 or $EmailCount >= 3 or $IPCount >= 3 or $ccCount >= 3){
  my $updateConsumerSQL = "update ConsumerOrder set Name_count = $NameCount, IP_Count = $IPCount, cc_count = $ccCount, Email_Count = $EmailCount where SONumber = $sorder";
    $sth = $dbhS->prepare($updateConsumerSQL); 
    if (!defined($sth) || !$sth->execute()) {print "\n(Update Consumer Counts)"; die;} 
    $sth->finish();
        
  }
}

sub Check {

  $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
  $sth = $dbh->prepare("select * from Session where ID = '" . esc($q->param('Session')) . "' and Store = '3'");
  if (!defined($sth) || !$sth->execute()) {print "\n(get session) "; die;}
  if ($sth->rows) {
    print <<_EOF_;
<table border="0" align="center" width="100%" height="100%">
  <tr>
    <td>
        To go back to Extreme Feet Clips
        <a href="http://www.extremefeetclips.com/">Click Here</a><br>
        To go to $the_domain
        <a href="http://www.$the_domain/">Click Here</a>
    </td>
  </tr>
</table>
_EOF_
    exit;
  }
  $sth->finish();

  if (  ($remote_country eq 'Turkey' && $q->param('Country') ne 'TR') || 
        ($remote_country eq 'Chile' && $q->param('Country') ne 'CL') ||
        ($remote_country eq 'Peru' && $q->param('Country') ne 'PE') ||
        ($remote_country eq 'Thailand' && $q->param('Country') ne 'TH') ||
        ($remote_country eq 'Algeria' && $q->param('Country') ne 'DZ') ||
        ($remote_country eq 'Egypt') ||
  ($remote_country eq 'China') ||
  ($remote_country eq 'Ukraine')
      ){
    $error = "Credit card number invalid - was it entered correctly? ERR-COINV";
    Main();
    exit;
  }
  if ($q->param('Grand_Total') > 500){
  $error = "You have tried to purchase more than our allowed order limit.  Please try multiple orders if you wish to order this amount";
  Main();
  exit;
  }
  if ($credit_card =~ /^37/) {
    $error = "We are currently not accepting American Express.";
    Main();
    exit;
  }
  if (!validate($credit_card)) {
    $error = "Credit card number invalid - was it entered correctly?";
    Main();
    exit;
  }
  if (cardtype($credit_card) ne $cc_name{$q->param('CardName')}) {
    $error = "Credit card number does not match Card Type";
    Main();
    exit;
  }
  my ($curmon, $curyear) = (localtime)[4,5];
  $curmon += 1; $curyear -= 100;
  if ($q->param('Expiration_Year') < $curyear or ($q->param('Expiration_Year') == $curyear and $q->param('Expiration_Month_Card') < $curmon)) {
    $error = "Your credit card expiration date must be this month and year or later.<br>$curmon < ".$q->param('Expiration_Month_Card')."  $curyear << ".$q->param('Expiration_Year');
    Main();
    exit;
  }

  if (($q->param('Country') eq "US") && ($q->param('State') eq "NA")) {
    $error = "If you pick US for your country, you must pick a State.\n (err-aim)";
    Main();
    exit;
  }

  if (($q->param('Country') eq "CA") && ($q->param('State') eq "NA")) {
    $error = "If you pick Canada for your country, you must pick a Province.\n (err-aip)";
    Main();
    exit;
  }

  if ($q->param('Email') !~ /[[:alnum:]\.\!\#\$\%\&\'\*\+\/\=\?\^\_\`\{\}\|\~\-]+@(?:[[:alnum:]\-]+\.)+[[:alpha:]]{2,6}/i) {
    $error = "You must enter a valid email address.\n (err-ais)";
    Main();
    exit;
  }

  foreach my $value ($q->param) {
    chomp $value;
    my $name = $value;
    $name =~ s/_/ /g;
    next if $value =~ /2$/;
    next if $value =~ /^gizmo/i;
    next if $value =~ /^clipcash/i;
    next if $value eq "Customer_ID";
    next if $value eq "Start";
    next if $value eq "Addl_Reqd";
    next if $value eq "State" and $q->param('Country') ne "US";
    next if $value eq "Zip_Code" and $q->param('Country') ne "US";
    next if (!$cc_addl_reqd and ($value eq 'Credit_Card_Bank' or $value eq 'Credit_Card_Phone' or $value eq 'Customer_Phone'));

    if ($value =~ /^email$/gi) {
      if ($q->param($value) ne $q->param('email2')) {
        $error = $q->param($value) . " and " . $q->param('email2') . " emails do not match (err-akp)\n";
        Main();
        exit;
      }
    }
    if ($value =~ /^Full_Name$/gi) {
  if ($q->param($value) =~ /^visa$/gi or
      $q->param($value) =~ /^mastercard$/gi or
      $q->param($value) =~ /^american express$/gi or
      $q->param($value) =~ /^discover$/gi or
      $q->param($value) =~ /^amex$/gi or
      $q->param($value) =~ /^hsbc$/gi or
      $q->param($value) =~ /^citi$/gi or
      $q->param($value) =~ /^citibank$/gi) {
    $error = "Name on card must be the Card Holder Name\n";
          Main();
          exit;
  } 
     }




    if (!$q->param($value) && !($value =~ /^pv/) && $value ne "Name" && $value ne 'referrer' && $value ne 'CampaignCode' && ($value ne 'TransID' && $OrderType ne 'Cam_Order') && $name ne 'Ebill' && $name ne 'eurobill' && $name ne 'RadioID') {
      $error = $name . " is required (err-ams)\n";
      Main();
      exit;
    }
  }
}

sub esc {
  my ($str) = $_[0];
  $str =~ s/(['\\])/\\$1/go if $str;
  return $str;
}

sub send_deny_error {
  my ($gateway, $paytot, $status, $authcode, $refnum, $avsres, $cvvres, $error, $auth_response, $fullresp, $bank_code) = @_;
  $mailer->open({Subject => 'FAILED Producer Order ('.$gateway.')',
                 To      => 'fraud@intermarkproductions.com',
                 From    => 'info@intermarkproductions.com',
    });
  print $mailer "Response info:\n\n";
  print $mailer "Status:        $status\n";
  print $mailer "AuthCode:      $authcode\n" if $authcode;
  print $mailer "AuthResponse:  $auth_response\n" if defined $auth_response;
  print $mailer "RefNum:        $refnum\n" if defined $refnum;
  print $mailer "AVS Result:    $avsres\n" if defined $avsres;
  print $mailer "CVV2 Result:   $cvvres\n" if defined $cvvres;
  print $mailer "Error:         $error\n" if defined $error;
  print $mailer "Bank Code:     $bank_code\n" if defined $bank_code;
  print $mailer "Full Response: $fullresp\n" if defined $fullresp;
  print $mailer "\nSubmitted info:\n\n";
  print $mailer 'Store:           ',$q->param('storeid'),$/;
  print $mailer 'Full Name:       ',$q->param('Full_Name'),$/ if defined $q->param('Full_Name');
  print $mailer 'Full Name:       ',$q->param('First_Name'),' ',$q->param('Last_Name'),$/ if defined $q->param('First_Name');
  print $mailer 'Address 1:       ',$q->param('Address_1'),$/;
  print $mailer 'Address 2:       ',$q->param('Address_2'),$/;
  print $mailer 'City:            ',$q->param('City'),$/;
  print $mailer 'State:           ',$q->param('State'),$/;
  print $mailer 'Country:         ',$q->param('Country'),$/;
  print $mailer 'Zip Code:        ',$q->param('Zip_Code'),$/;
  print $mailer 'Email:           ',$q->param('Email'),$/;
  print $mailer 'Grand Total:     ',$paytot,$/;
  print $mailer 'IP Address:      ',$ENV{'REMOTE_ADDR'},$/;
  print $mailer 'Country from IP: ',$remote_country,$/;
  print $mailer $maxmind_ccfs_info,$/;
  $mailer->close;
      my @names = $q->param;
                        my $fraudOrderData = "This is the Order Information\n\n";
      foreach my $names (@names) {
        chomp $names;
                                if ($names =~ /Credit_Card_Number/i or $names =~ /cvv/i or $names =~ /cvm/i) {}
                                else{
                                        $fraudOrderData .= "$names : ". $q->param($names) . "\n";
                                }
      }
    
    # Get the aes value from the db w/a select. Then use the val for the INSERT.
    my $enc_val_cc = Encrypt($q->param('Credit_Card_Number'), $ccEncryptString);
    my $enc_val_full_name = Encrypt($q->param('Full_Name'), $nameEncryptString);
    my $enc_val_email = Encrypt($q->param('Email'), $emailEncryptString);
    
    
    #insert into the fraud table
     my $fraudSQL = "insert into Track_Denied
       set
        Credit_Card = '" . esc($enc_val_cc) . "',
        Name = '" . esc($enc_val_full_name) . "',
        Email = '" . esc($enc_val_email) . "',
        ProducerID = " . $q->param('storeid') . ",
        Amount = " . $q->param('Grand_Total') . ",
        IPAddress = inet_aton('$remote_addr'),
        Gateway = '$gateway',
        Status = '$status',
        AuthCode      = '$authcode',
        AuthResponse  = '$auth_response',
        RefNum        = '$refnum',
        AVS_Result    = '$avsres',
        CVV2_Result   = '$cvvres',
        Error         = '$error',
        Bank_Code     = '$bank_code',
        Full_Response = '$fullresp',
        OrderDetails = '" . esc($fraudOrderData) . "',
        Max_AnonymousProxy = '$anonymousProxy',
        Max_Country = '$MaxCountry',
        Max_Distance = '$MaxDistance',
        Max_HighRiskCountry = '$MaxHighRisk',
        Max_IP_Region = '$MaxIPRegion',
        Max_MaxMindID = '$MaxID',
        Max_ProxyScore = 0,
        Max_Score = 0,
        Max_SpamScore = '$MaxSpamScore',
        Max_IP_ISP = '$MaxISP',
        Max_IP_ORG = '$MaxORG',
  MaxMindDetails = '$maxmind_ccfs_info',
  Service = '$service'";
                                                             

    $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
      $sth = $dbhS->prepare($fraudSQL);
      if (!defined($sth) || !$sth->execute()) {print "\n(Could not add Denied card info to Database) <br>\n"; die;}
      $sth->finish;
      $dbhS->disconnect();
}

sub pay_plugnpay {
  my $paytot = shift;

  my ($CamAuth, $CamTotal);
  my $AllowCamOrder = 0;
  if ($OrderType eq 'Cam_Order'){
        my ($CamAuth, $CamTotal);
        $sth = $dbhS->prepare("select Authorized, Total from CamAuth where cc = aes_encrypt(" . $dbhS->quote($credit_card) . ",'$ccEncryptString')");
        if (!defined($sth) || !$sth->execute()) {die $q->header() . "\n\ngather the Authorized Cam Status " .  $dbhS->errstr . "<br>\n";}
        $sth->bind_columns(\$CamAuth, \$CamTotal);
        $sth->fetch();
        $sth->finish();
        if ((defined($CamAuth) && ($CamAuth == 1 || ($CamTotal + $paytot) < 500 )) || not(defined($CamAuth))){
                        if (not(defined($CamAuth))) {
                                # Get the aes value from the db w/a select. Then use the val for the INSERT.
                                my $enc_val_cc = Encrypt($credit_card, $ccEncryptString);

                                                         my $sqlstatement = "Insert into CamAuth values ('" . $dbhS->quote($enc_val_cc) . "', '". $q->param('Full_Name'). "', '". $q->param('Zip_Code'). "', 0, 0)";
                   $dbhS->do($sqlstatement);
           }
                $AllowCamOrder = 1;

        }
  }
#END CAMBILL
 if (($OrderType eq 'Cam_Order' and $AllowCamOrder == 1) || $OrderType ne 'Cam_Order'){

  open LOG, ">> /home/OrderSystem/public_html/SecureProcess/pnp.log";
  print LOG scalar localtime;
  #print $q->header(), " I got to here\n $plugandpay, $paytot"; exit;
  my %pnphash = (
  'publisher-name'           => $plugandpay,
  'card-amount'              => $paytot,
  mode                  => 'auth',
  authtype                  => 'authpostauth',
  #convert                  => 'underscores',
  'card-name'                => $q->param('Full_Name'),
  'card-address1'            => $q->param('Address_1'),
  'card-city'           => $q->param('City'),
  'card-state'            => $q->param('State'),
  'card-zip'              => $q->param('Zip_Code'),
  'card-country'          => $q->param('Country'),
  'card-number'           => $credit_card,
  'card-exp'              => $q->param('Expiration_Month_Card') . '/' . $q->param('Expiration_Year'),
  'card-cvv'              => $q->param('cvmvalue'),
  ipaddress             =>  $ENV{'REMOTE_ADDR'},
        );
  my %query;
  foreach my $key (sort keys %pnphash) {
     my $value = $pnphash{$key};
     $value =~ s/%(..)/pack('c',hex($1))/eg;
     $value =~ s/\+/ /g;
     $query{$key} = $value;
  }

  my @pnparray = %query;

  # does some input testing to make sure everything is set correctly
   my $payment = pnpremote->new(@pnparray) || die $q->header(), " Prodcess not working\n";
  #
  # # does the actual connection and purchase. Transaction result is returned in query hash.
  # # variable to test for success is $query{'FinalStatus'}.  Possible values are success, badcard or problem
  #
   my %pnpreturns = $payment->purchase();
  #
  # # Post Transaction processing. (Optional)
  # # Depending on desired behavior and values of 'success-link', 'badcard-link' & 'problem-link'
  # # this script call either redirect to a web page or perform a post to a different script.
  # # if you will performing your own validity test on the transaction results, you may comment out the follow line.
  # $payment->final();
  ##
#  exit;
   
    my $r_approved     = $pnpreturns{'FinalStatus'};
    my $r_ref          = $pnpreturns{''};
    my $r_ordernum     = $pnpreturns{'orderID'};
    my $r_avs          = $pnpreturns{'avs_code'};
    my $r_vpasresponse = $pnpreturns{'auth_code'};
    my $r_authresponse = $pnpreturns{'FinalStatus'};
    my $r_message      = $pnpreturns{'FinalStatus'} . " - " . $pnpreturns{'avs_code'};
    my $r_error        = $pnpreturns{'MErrMsg'};
                     

    if ($r_error =~ /Gateway\s*\w*\s*offline/i) {
      # UMerror=Gateway temporarily offline.  Please try again shortly.
      print LOG "\n!!!!!" . (scalar localtime) . " r_error matched, buyer got 'gateway offline' error\n";
      close LOG;
      $error = '<span style="font-size:24px">The credit card payment gateway is temporarily offline.<br>Please try again later.</span>';
      send_deny_error('PlugAndPay', $paytot, $r_approved, $r_ref, $r_ordernum, $r_avs,  $r_vpasresponse, $r_error);
      Main();
      exit;
    }
    if ($r_approved =~ /success/gi) {
      print LOG "\nApproved $the_domain\n";
      print LOG "item count: ",scalar @uniqids,"\n";
      close LOG;
      $log_in = "$remote_addr-$r_ordernum";
      
      Add($paytot);
    } else {
      print LOG "\nDenied\n";
      print LOG "\n$r_approved, ::: $r_ref, ::: $r_ordernum, ::: $r_avs, ::: $r_vpasresponse, :: $r_error\n";
      close LOG;
      $error = "Your credit card has been denied. (1 pnp err-aov )";
      $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
      # Get the aes value from the db w/a select. Then use the val for the INSERT.
      my $enc_val_cc = Encrypt($credit_card, $ccEncryptString);
    
      $dbhS->do("replace into RateLimitCC set card = '$enc_val_cc', last_use = NOW()");
      send_deny_error('plugnpay', $paytot, $r_approved, $r_ref,    $r_ordernum, $r_avs,  $r_vpasresponse, $r_error);
      Main();
      exit;
    }
  }
  else  {
      print $q->redirect('http://www.c4slive.com/AuthorizeCam.html');
  }

}
sub pay_routemerrick {
  my $paytot = shift;
  my $OldRoutedCC = $cc;
# Is this store configured for a gateway?
  $sth = $dbh->prepare("
  select
  m.cc, m.descriptor, m.hold_percent,
  m.umkey,
  m.ePNAccount,
  m.goEMerch, m.goEPasswd,
  m.authNname, m.authNpasswd,
  m.linkPconfig, m.linkPkeyfile,
  m.capstoneID, m.capstonePasswd,
  m.paygeaID, m.paygeaPW, m.paygeaAccount,
  m.plugandpay
  from Merchant_Account m
  where m.cc = 905
  ");
$dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
if (!defined($sth) || !$sth->execute()) {die $q->header() . "\n\n(select prodmerch) STH: " . ":: " . $dbh->errstr . "<br>\n";}
$sth->bind_columns(\$cc, \$descriptor, \$hold_percent, \$umkey, \$ePNAccount, \$goEMerch, \$goEPasswd, \$authNname, \$authNpasswd, \$linkPconfig, \$linkPkeyfile, \$cpstnID, \$cpstnPW, \$paygeaID, \$paygeaPW, \$paygeaAccount, \$plugandpay);
$sth->fetch();


  
  open LOG, ">> /home/OrderSystem/public_html/SecureProcess/merrick_pnp.log";
  print LOG scalar localtime;
  print LOG "Original CC: $OldRoutedCC \n";
  my %pnphash = (
  'publisher-name'           => $plugandpay,
  'card-amount'              => $paytot,
  mode                  => 'auth',
  authtype                  => 'authpostauth',
  #convert                  => 'underscores',
  'card-name'                => $q->param('Full_Name'),
  'card-address1'            => $q->param('Address_1'),
  'card-city'           => $q->param('City'),
  'card-state'            => $q->param('State'),
  'card-zip'              => $q->param('Zip_Code'),
  'card-country'          => $q->param('Country'),
  'card-number'           => $credit_card,
  'card-exp'              => $q->param('Expiration_Month_Card') . '/' . $q->param('Expiration_Year'),
  'card-cvv'              => $q->param('cvmvalue'),
  ipaddress             =>  $ENV{'REMOTE_ADDR'},
        );
  my %query;
  foreach my $key (sort keys %pnphash) {
     my $value = $pnphash{$key};
     $value =~ s/%(..)/pack('c',hex($1))/eg;
     $value =~ s/\+/ /g;
     $query{$key} = $value;
  }

  my @pnparray = %query;

  # does some input testing to make sure everything is set correctly
   my $payment = pnpremote->new(@pnparray);
  #
  # # does the actual connection and purchase. Transaction result is returned in query hash.
  # # variable to test for success is $query{'FinalStatus'}.  Possible values are success, badcard or problem
  #
   my %pnpreturns = $payment->purchase();
  #
  # # Post Transaction processing. (Optional)
  # # Depending on desired behavior and values of 'success-link', 'badcard-link' & 'problem-link'
  # # this script call either redirect to a web page or perform a post to a different script.
  # # if you will performing your own validity test on the transaction results, you may comment out the follow line.
  # $payment->final();
  ##
#  exit;
   
    my $r_approved     = $pnpreturns{'FinalStatus'};
    my $r_ref          = $pnpreturns{''};
    my $r_ordernum     = $pnpreturns{'orderID'};
    my $r_avs          = $pnpreturns{'avs_code'};
    my $r_vpasresponse = $pnpreturns{'auth_code'};
    my $r_authresponse = $pnpreturns{'FinalStatus'};
    my $r_message      = $pnpreturns{'FinalStatus'} . " - " . $pnpreturns{'avs_code'};
    my $r_error        = $pnpreturns{'MErrMsg'};
                     

    if ($r_error =~ /Gateway\s*\w*\s*offline/i) {
      # UMerror=Gateway temporarily offline.  Please try again shortly.
      print LOG "\n!!!!!" . (scalar localtime) . " r_error matched, buyer got 'gateway offline' error\n";
      close LOG;
      $error = '<span style="font-size:24px">The credit card payment gateway is temporarily offline.<br>Please try again later.</span>';
      send_deny_error('MerrickFromSuncoast', $paytot, $r_approved, $r_ref, $r_ordernum, $r_avs,  $r_vpasresponse, $r_error);
      Main();
      exit;
    }
    if ($r_approved =~ /success/gi) {
      print LOG "\nApproved $the_domain\n";
      print LOG "item count: ",scalar @uniqids,"\n";
      close LOG;
      $log_in = "$remote_addr-$r_ordernum";
      
      Add($paytot);
    } else {
      print LOG "\nDenied\n\t$r_vpasresponse\n\t$r_error\n";
      close LOG;
      $error = "Your credit card has been denied. (2 pnp err-aov )";
      $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
      # Get the aes value from the db w/a select. Then use the val for the INSERT.
      my $enc_val_cc = Encrypt($credit_card, $ccEncryptString);
    
      $dbhS->do("replace into RateLimitCC set card = '" . $dbhS->quote($enc_val_cc) . "', last_use = NOW()");
      send_deny_error('plugnpaySuncoastViaMerrick', $paytot, $r_approved, $r_ref,    $r_ordernum, $r_avs,  $r_vpasresponse, $r_error);
      Main();
      exit;
    }
}

sub pay_usaepay {
  my $paytot = shift;
  my $ordertype = 'SALE';
  open LOG, ">> /home/OrderSystem/public_html/SecureProcess/usaepay.log";
  print LOG scalar localtime;
  my $req = POST 'https://www.usaepay.com/gate.php', [
  UMkey           => $umkey,
  UMcard          => $credit_card,
  UMexpir         => $q->param('Expiration_Month_Card') . $q->param('Expiration_Year'),
  UMamount        => $paytot,
  UMdescription   => '',
  UMcvv2          => $q->param('cvmvalue'),
  UMcustemail     => $q->param('Email'),
  UMcustreceipt   => 'No',
  UMname          => $q->param('Full_Name'),
  UMstreet        => $q->param('Address_1'),
  UMzip           => $q->param('Zip_Code'),
  UMip            => $ENV{'REMOTE_ADDR'},
  UMcommand       => 'sale',
  UMtestmode      => 0
  ];
  #print LOG "\nReq: $umkey ";#, $req->{'_content'};
  my $res = $ua->request($req);
  print LOG "\nRes: ", $res->{'_content'};
  if ($res->is_success) {
    my $m = new CGI($res->content());
    my $r_linkpoint    = $res->content();
    my $r_code         = $res->content();
    my $r_approved     = $m->param('UMstatus');
    my $r_ref          = $m->param('UMauthCode');
    my $r_ordernum     = $m->param('UMrefNum');
    my $r_avs          = $m->param('UMavsResult');
    my $r_vpasresponse = $m->param('UMcvv2Result');
    my $r_authresponse = $m->param('UMavsResult');
    my $r_message      = $m->param('UMavsResult') . " - " . $m->param('UMcvv2Result');
    my $r_error        = $m->param('UMerror');

    if ($r_error =~ /Gateway\s*\w*\s*offline/i) {
      # UMerror=Gateway temporarily offline.  Please try again shortly.
      print LOG "\n!!!!!" . (scalar localtime) . " r_error matched, buyer got 'gateway offline' error\n";
      close LOG;
      $error = '<span style="font-size:24px">The credit card payment gateway is temporarily offline.<br>Please try again later.</span>';
      send_deny_error('usaepay', $paytot, $r_approved, $r_ref,    $r_ordernum, $r_avs,  $r_vpasresponse, $r_error);
      Main();
      exit;
    }
    if ($r_approved =~ /Approved/gi) {
      print LOG "\nApproved $the_domain\n";
      print LOG "item count: ",scalar @uniqids,"\n";
      close LOG;
      $log_in = "$remote_addr-$r_ordernum";
      Add($paytot);
    } else {
        print LOG "\nDenied\n";
        close LOG;
        $error = "Your credit card has been denied. (err-aov)";
        $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
        # Get the aes value from the db w/a select. Then use the val for the INSERT.
        my $enc_val_cc = Encrypt($credit_card, $ccEncryptString);
    
        $dbhS->do("replace into RateLimitCC set card = '" . $dbhS->quote($enc_val_cc) . "', last_use = NOW()");
          if ($q->param('Country') ne 'US' and $cc == 8 and "CHAGEN" eq "MODIFIED") {
             send_deny_error('Tropical Failed Sending To Suncoast', $paytot, $r_approved, $r_ref,    $r_ordernum, $r_avs,  $r_vpasresponse, $r_error);
          } else {
             send_deny_error('usaepay', $paytot, $r_approved, $r_ref,    $r_ordernum, $r_avs,  $r_vpasresponse, $r_error);
          }
        #Reroute US based cards to Merrick.
        if ($q->param('Country') ne 'US' and $cc == 8 and "CHAGEN" eq "MODIFIED") {
          pay_paygea_DefaultSuncoast($paytot);
        }
      Main();
      exit;
    }
  } else {
    print LOG "\n!!!!! " . (scalar localtime) . "Req failed, buyer got 'gateway down' error\n";
    close LOG;
    $error = "There has been an error with this process (probably because the payment gateway is down). Please try again later. (err-aqy)";
    Main();
    exit;
  }
}

sub pay_paygate {
  my $paytot = shift;
  open LOG, ">> /home/OrderSystem/public_html/SecureProcess/PayGate.log";
  print LOG scalar localtime;
  my $last = '';
  my $full_name = $q->param('Full_Name');
  my ($first, @rest) = split(/\s/,$full_name);
  if($rest[1] ne '') { $last = $rest[1];} else {$last = $rest[0];}
  if ($last eq ''){ $last = $first;}
  #my $req = POST 'https://paygate.epg-1.com/cc4/start_transaction.php', [
  my $req = POST 'https://api.epg-services.com/V1/paygate/start_transaction.php', [
  CustomerID    => $paygateid,
  CustomerPassword  => $paygatepw,
  ReferenceNumber => $rande,
  TransType   => 'sale',
  Amount    => $paytot,
  Currency    => 'USD',
  MerchantInfo    => 'www.sun-tropic.com;admin@sun-tropic.com',
  CreditCardNumber      => $credit_card,
  CreditCardType  => $q->param('CardName'),
  CreditCardCVVCode => $q->param('cvmvalue'),
  CreditCardExpireMonth => $q->param('Expiration_Month_Card'),
  CreditCardExpireYear  => '20' . $q->param('Expiration_Year'), 
  CardholderFirstName => $first,
  CardholderLastName  => $last,
  CardholderAddress => $q->param('Address_1'),
  CardholderZipCode => $q->param('Zip_Code'),
  CardholderCity  => $q->param('City'),  
  CardholderState => $q->param('State'),
  CardholderCountry => $q->param('Country'),
  CardholderEmail => $q->param('Email'),
  CardholderIPAddress => $ENV{'REMOTE_ADDR'}
  ];
  #print LOG "\nReq: $umkey ";#, $req->{'_content'};
  my $res = $ua->request($req);
  print LOG "\nRes: ", $res->{'_content'};
  print LOG "\nData: :", $q->param('Country'), ":";
  if ($res->is_success) {
    my $m = new CGI($res->content());
    my $result  = $m->param('Result');
    my $result_code = $m->param('ResultCode');
    my $result_text = $m->param('ResultText');
    my $trans_id = $m->param('TransactionID');
    my $reference = $m->param('Reference');
    my $status_text = $m->param('Status');

    if ($result eq 'ERROR') {
      # UMerror=Gateway temporarily offline.  Please try again shortly.
      print LOG "\n!!!!!" . (scalar localtime) . " Result was ERROR, buyer got 'gateway offline' error\n";
      close LOG;
      $error = '<span style="font-size:24px">The credit card payment gateway is temporarily offline.<br>Please try again later.</span>';
      send_deny_error('paygate', $paytot, $result_code, $result_text,    $trans_id, '',  $reference, $status_text);
      Main();
      exit;
    }
    if ($result eq "OK") {
      print LOG "\nApproved $the_domain\n";
      print LOG "item count: ",scalar @uniqids,"\n";
      close LOG;
      $log_in = "$remote_addr-$trans_id";
      #print $log_in;
  Add($paytot);
    } else {
        print LOG "\nDenied\n";
        close LOG;
        $error = "Your credit card has been denied. (err-aov)";
        $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
        # Get the aes value from the db w/a select. Then use the val for the INSERT.
        my $enc_val_cc = Encrypt($credit_card, $ccEncryptString);
    
        $dbhS->do("replace into RateLimitCC set card = '" . $dbhS->quote($enc_val_cc) . "', last_use = NOW()");
        #send_deny_error('paygate', $paytot, $result_code, $result_text,    $trans_id, '',  $reference, $status_text);
        if ($cc == 909) {
          send_deny_error('paygate Sending to Merrick', $paytot, $result_code, $result_text,    $trans_id, '',  $reference, $status_text);
        } else {
          send_deny_error('paygate', $paytot, $result_code, $result_text,    $trans_id, '',  $reference, $status_text);
        }
      
        #Reroute US based cards to Merrick.
        if ($cc == 909) {
          pay_routemerrick($paytot);
        }
      #send_deny_error('usaepay', $paytot, $r_approved, $r_ref,    $r_ordernum, $r_avs,  $r_vpasresponse, $r_error);
      Main();
      exit;
    }
  } else {
    print LOG "\n!!!!! " . (scalar localtime) . "Req failed, buyer got 'gateway down' error\n";
    close LOG;
    $error = "There has been an error with this process (probably because the payment gateway is down). Please try again later. (err-aqy)";
    Main();
    exit;
  }
}

sub pay_capstone {
  my $paytot = shift;
  my $action = 'authpostauth';
  my $req = POST 'https://www.capstonepay.com/cgi-bin/client/transaction.cgi', [
  merchantid       => $cpstnID,
  account_password => $cpstnPW,
  action           => $action,
  amount           => $paytot,
  name             => $q->param('Full_Name'),
  address1         => $q->param('Address_1'),
  address2         => $q->param('Address_2'),
  city             => $q->param('City'),
  state            => $q->param('State'),
  postal           => $q->param('Zip_Code'),
  country          => $q->param('Country'),
  email            => $q->param('Email'),
  ipaddress        => $remote_addr,
  card_num         => $credit_card,
  card_exp         => $q->param('Expiration_Month_Card') . $q->param('Expiration_Year'),
  card_cvv         => $q->param('cvmvalue'),
  bank_name        => $q->param('Credit_Card_Bank'),
  bank_phone       => $q->param('Credit_Card_Phone'),
  orderid          => $rande,
  custom4          => 'TranType:clips4sale.com',
  ];
  my $res = $ua->request($req);
  if ($res->is_success) {
    my $m = new CGI($res->content());
    my $stat           = $m->param('status');
    my $stat_code      = $m->param('status_code');
    my $auth_code      = $m->param('auth_code');
    my $avs_resp       = $m->param('avs_resp');
    my $cvv_resp       = $m->param('cvv_resp');
    my $orderid        = $m->param('orderid');
    my $stat_msg       = $m->param('status_msg');
    my $bank_code      = $m->param('bank_code');

    if ($stat =~ /good/i) {
     $log_in = "$remote_addr-$auth_code";
     Add($paytot);
    } else {
      open BCL, ">> /home/OrderSystem/public_html/SecureProcess/capstn.log";
      printf BCL "Code: %5.5s  Type: %s\n", $bank_code, $q->param('CardName');
      close BCL;
      $error = "Your credit card has been denied. (err-aov)";
      $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
      # Get the aes value from the db w/a select. Then use the val for the INSERT.
      my $enc_val_cc = Encrypt($credit_card, $ccEncryptString);
    
      $dbhS->do("replace into RateLimitCC set card = '" . $dbhS->quote($enc_val_cc) . "', last_use = NOW()");
      my $cardtype = cardtype($credit_card);
      $dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
      my $bank_code_msg = $dbh->selectrow_array("select resptext from capstone_codes where cardtype = '$cardtype' and respcode = '$bank_code'");
      $bank_code_msg = $bank_code unless $bank_code_msg;
      my $fullresp = "\n";
      foreach my $param ($m->param) {
        $fullresp .= "     $param  =>  " . $m->param($param) . "\n";
      }
      send_deny_error('capstone', $paytot, $stat,   $auth_code, $orderid, $avs_resp, $cvv_resp, $stat_msg, undef,          $fullresp,     $bank_code_msg);
      #              ($gateway,   $paytot, $status, $authcode,  $refnum,  $avsres,   $cvvres,   $error,    $auth_response, $fullresp,     $bank_code)
      Main();
      exit;
    }
  } else {
    $error = "There has been a error with this process. Please try again. (err-aqy)";
    Main();
    exit;
  }
}

sub pay_eproc {
  my $paytot = shift;
  my $ordertype = 'SALE';
  my $cvmindicator;
  if ($q->param('cvmvalue')) {$cvmindicator = 1;} else {$cvmindicator = 9;}

  my $req = POST 'https://www.eProcessingNetwork.Com/cgi-bin/tdbe/transact.pl',
  [
  ePNAccount => $ePNAccount,
  CardNo     => $credit_card,
  ExpMonth   => $q->param('Expiration_Month_Card'),
  ExpYear    => $q->param('Expiration_Year'),
  Total      => $paytot,
  Address    => $q->param('Address_1'),
  Zip        => $q->param('Zip_Code'),
  CVV2Type   => $cvmindicator,
  CVV2       => $q->param('cvmvalue'),
  HTML       => 'NO'
  ];
  my $res = $ua->request($req);
  if ($res->is_success) {
    my $content = $res->content;
    $content =~ s/<html><body>//gi;
    $content =~ s/<\/body><\/html>//gi;

    my ($approval, $amess, $cvv) = split(/,/, $content);
    if (!$cvv) {$cvv = '';}
    if (!$amess) {$amess = '';}
    $approval =~ s/"//g;
    $amess =~ s/"//g;
    $cvv =~ s/"//g;

    my ($response, $ticket) = split(/\s+/, $approval);

    my $r_approved     = substr($approval, 0, 1);
    my $r_ref          = substr($approval, 1, 16);
    my $r_ordernum     = $ticket;
    my $r_avs          = $amess;
    my $r_authresponse = $cvv;
    my $r_code         = $res->content;

    if ($r_approved eq "Y") {
      $log_in = "$remote_addr-$r_ordernum";
      Add($paytot);
    } else {
      $error = "Your credit card has been denied. (err-asb)";
      $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
      # Get the aes value from the db w/a select. Then use the val for the INSERT.
      my $enc_val_cc = Encrypt($credit_card, $ccEncryptString);
    
      $dbhS->do("replace into RateLimitCC set card = '" . $dbhS->quote($enc_val_cc) . "', last_use = NOW()");
      send_deny_error('eProcessingNetwork', $paytot, $r_approved, $r_ref,    $r_ordernum, $r_avs,  $r_authresponse, undef,  undef,          $r_code);
      #              ($gateway,             $paytot, $status,     $authcode, $refnum,     $avsres, $cvvres,         $error, $auth_response, $fullresp, $bank_code)
      Main();
      exit;
    }
  } else {
    $error = "There has been a error with this process. Please try again. (err-are)";
    Main();
    exit;
  }
}



sub pay_firepay {
    my $paytot = shift;
    my $gtot = sprintf "%.2f", $paytot;

  my $last = '';
  my $full_name = $q->param('Full_Name');
    my ($first, @rest) = split(/\s/,$full_name);
    if($rest[1] ne '') { $last = $rest[1];} else {$last = $rest[0];}
    if ($last eq ''){ $last = $first;}
  
  my %cardtype;
  $cardtype{Mastercard} = 'MC';
    $cardtype{Visa} = 'VI';
    $cardtype{Discover} = 'DI';
    $cardtype{Amercan_Express} = 'AM';
    my $cardType;
    if ($q->param('CardName') eq 'American Express') {
          $cardType = 'American_Express';
    } else {
        $cardType = $q->param('CardName');
    }
  my $StateOrRegion = '';
  if ($q->param('Country') eq 'US' or $q->param('Country') eq 'CA'){
    $StateOrRegion = '<state>'.$q->param('State').'</state>';
  } else {
    $StateOrRegion = '<region>'.$q->param('State').'</region>';
  }

    my $xml_out = ''.
    '<merchantAccount>'.
      '<accountNum>'.$firePayNum.'</accountNum>'.
      '<storeID>'.$fireID.'</storeID>'.
      '<storePwd>'.$firePWD.'</storePwd>'.
    '</merchantAccount>'.
    '<merchantRefNum>'.$rande.'</merchantRefNum>'.
    '<amount>'.$gtot.'</amount>'.
    '<card>'.
      '<cardNum>'.$credit_card.'</cardNum>'.
      '<cardExpiry>'.
        '<month>'.$q->param('Expiration_Month_Card').'</month>'.
        '<year>20'.$q->param('Expiration_Year').'</year>'.
      '</cardExpiry>'.
      '<cardType>'.$cardtype{$cardType}.'</cardType>'.
      '<cvdIndicator>1</cvdIndicator>'.
      '<cvd>'.$q->param('cvmvalue').'</cvd>'.
    '</card>'.
    '<billingDetails>'.
        '<cardPayMethod>WEB</cardPayMethod>'.
        '<firstName>'.$first.'</firstName>'.
        '<lastName>'.$last.'</lastName>'.
        '<street>'.$q->param('Address_1').'</street>'.
        '<city>'.$q->param('City').'</city>'.
        $StateOrRegion.
        '<country>'.$q->param('Country').'</country>'.
        '<zip>'.$q->param('Zip_Code').'</zip>'.
    '</billingDetails>';
    #'<customerIP>'.$remote_addr.'</customerIP>';

  my $fireForm = 'txnMode=ccPurchase&txnRequest=<ccAuthRequestV1 xmlns="http://www.optimalpayments.com/creditcard/xmlschema/v1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.optimalpayments.com/creditcard/xmlschema/v1">' . $xml_out . '</ccAuthRequestV1>';

    my $ua = LWP::UserAgent->new(timeout => 30);
    my $req = HTTP::Request->new('POST', 'https://webservices.optimalpayments.com/creditcardWS/CreditCardServlet/v1');
  $req->content_type('application/x-www-form-urlencoded');
    #$req->header(Content_Type => 'text/xml');
    $req->content($fireForm);
    my $res = $ua->request($req);
    if ($res->is_success) {
      my $content = $res->as_string;
      my @fireResponse = split(/\n/,$content);
    my $fireResponseFinal = '';
    foreach my $fireResponseText (@fireResponse){
      if ($fireResponseText =~ /</ and !($fireResponseText =~ /ccAuthorize/)){
        $fireResponseFinal .= $fireResponseText;
      }
    }
    my $r = XMLin($fireResponseFinal);

    #open ( OUTFILE, ">> /tmp/EPXstatus_web_services.txt" )

        #or die ( "Cannot open file : $! " );
    #print OUTFILE $r->{'decision'} , " this is r's data" ,  $r->{description} , " $fireForm\n\n";
    #print ( OUTFILE "$content\n" );

    #close ( OUTFILE );
    #exit;

    
  
        if($r->{'decision'} eq 'ACCEPTED') {
            #  approved
            $log_in = $remote_addr.'-'.$r->{'confirmationNumber'};
            Add($paytot);
        } else {
            $error = 'An error occurred while attempting to authorize your credit card. Please try again. (err-ath)' if $r->{'decision'} eq 'ERROR';
            $error = 'Your credit card has been denied. (err-avk)' if $r->{'decision'} eq 'DECLINED';
            $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
      # Get the aes value from the db w/a select. Then use the val for the INSERT.
      my $enc_val_cc = Encrypt($credit_card, $ccEncryptString);
  
      if ($r->{'decision'} eq 'DECLINED'){
        my $RLCC = $dbhS->prepare("replace into RateLimitCC set card = ?, last_use = NOW()");
        $RLCC->execute($enc_val_cc);
        $RLCC->finish();
      }
      #$dbhS->do("replace into RateLimitCC set card = '" . $dbhS->quote($enc_val_cc) . "', last_use = NOW()") if $r->{'decision'} eq 'DECLINED';
            #Send Transactions to Merrick for cc 5.
      if ($cc == 5 || $cc == 911) {
              send_deny_error('FirePayStKitts Sending To Merrick', $paytot, $r->{'description'}, $r->{'code'}, $r->{'confirmationNumber'}, $r->{'avsResponse'}, $r->{'cvdResponse'}, $r->{'detail'}{'value'}, $r->{'detail'}{'value'});
            } else {
              #send_deny_error('FirePayStKitts', $paytot, $r->{'description'}, $r->{'code'}, $r->{'confirmationNumber'}, $r->{'avsResponse'}, $r->{'cvdResponse'}, $r->{'detail'}{'value'}, $r->{'detail'}{'value'});
              send_deny_error('FirePayStKitts', $paytot, $r->{'decision'}, $r->{'code'}, $r->{'confirmationNumber'}, $r->{'avsResponse'}, $r->{'cvdResponse'}, $r->{'description'}, $r->{'detail'}{'value'});
            }
        
            #Reroute failed cards to Merrick.
            if ($cc == 5 || $cc == 911) {
              pay_routemerrick($paytot);
            }
            Main();
            exit;
        }
    } else {
      $error = "There has been a error with this process. Please try again. (err-axn)";
      Main();
      exit;
    } 
}








sub pay_goEmerchant {
  my $paytot = shift;
  my $gtot = sprintf "%.2f", $paytot;
  my $xml_out = '
  <?xml version="1.0" encoding="UTF-8"?>
  <TRANSACTION>
  <FIELDS>
  <FIELD KEY="merchant">'.$goEMerch.'</FIELD>
  <FIELD KEY="password">'.$goEPasswd.'</FIELD>
  <FIELD KEY="operation_type">sale</FIELD>
  <FIELD KEY="order_id">'.$rande.'</FIELD>
  <FIELD KEY="total">'.$gtot.'</FIELD>
  <FIELD KEY="card_name">'.$q->param('CardName').'</FIELD>
  <FIELD KEY="card_number">'.$credit_card.'</FIELD>
  <FIELD KEY="card_exp">'.$q->param('Expiration_Month_Card').$q->param('Expiration_Year').'</FIELD>
  <FIELD KEY="cvv2">'.$q->param('cvmvalue').'</FIELD>
  <FIELD KEY="owner_name">'.$q->param('Full_Name').'</FIELD>
  <FIELD KEY="owner_street">'.$q->param('Address_1').'</FIELD>
  <FIELD KEY="owner_city">'.$q->param('City').'</FIELD>
  <FIELD KEY="owner_state">'.$q->param('State').'</FIELD>
  <FIELD KEY="owner_zip">'.$q->param('Zip_Code').'</FIELD>
  <FIELD KEY="owner_country">'.$q->param('Country').'</FIELD>
  <FIELD KEY="recurring">0</FIELD>
  <FIELD KEY="recurring_type"></FIELD>
  </FIELDS>
  </TRANSACTION>';

  my $ua = LWP::UserAgent->new(timeout => 30);
  my $req = HTTP::Request->new('POST', 'https://www.goemerchant4.com/trans_center/gateway/xmlgateway.cgi');
  $req->header(Content_Type => 'text/xml');
  $req->content($xml_out);
  my $res = $ua->request($req);
  if ($res->is_success) {
    my $content = $res->content;
    my $r = XMLin($content);
    my %resp = map { $_->{'KEY'}, $_->{'content'} } @{$r->{'FIELDS'}{'FIELD'}};

    if ($resp{'status'} == 1) {
      # approved
      $log_in = $remote_addr.'-'.$resp{'reference_number'};
      Add($paytot);
    } else {
      $error = 'An error occurred while attempting to authorize your credit card. Please try again. (err-ath)' if $resp{'status'} == 0;
      $error = 'Your credit card has been denied. (err-avk)' if $resp{'status'} == 2;
      $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
      # Get the aes value from the db w/a select. Then use the val for the INSERT.
      my $enc_val_cc = Encrypt($credit_card, $ccEncryptString);
    
      $dbhS->do("replace into RateLimitCC set card = '" . $dbhS->quote($enc_val_cc) . "', last_use = NOW()") if $resp{'status'} == 2;
      send_deny_error('goEmerchant', $paytot, $resp{'status'}, $resp{'auth_code'}, $resp{'reference_number'}, $resp{'avs_code'}, $resp{'cvv2_code'}, $resp{'error'}, $resp{'auth_response'});
      #              ($gateway,      $paytot, $status,         $authcode,          $refnum,                   $avsres,           $cvvres,            $error,         $auth_response,         $fullresp, $bank_code)
      Main();
      exit;
    }
  } else {
    $error = "There has been a error with this process. Please try again. (err-axn)";
    Main();
    exit;
  }
}

sub pay_paygea {
  my $paytot = shift;
  my $fullname = $q->param('Full_Name');
  $fullname =~ s/\s+/ /g;
  $fullname =~ s/^\s+//;
  $fullname =~ s/\s+$//;
  my $emailAddress = $q->param('Email');
  $emailAddress =~ s/^\s+//;
  my $CountryID = $countries_num{$q->param('Country')};
  my ($first, $last) = split(/\s/,$fullname);
  my $cvvValue = $q->param('cvmvalue');
  $cvvValue =~ s/\s+//g;
  if ($last eq ''){ $last = $first;}
  my $req = POST 'https://secure.paygea.com/secure/spsprocess', [
  sps_merchant       => $paygeaID,
  sps_orderid        => $rande,
  sps_amount         => $paytot,
  sps_firstname      => $first,
  sps_lastname       => $last,
  sps_cardnumber     => $credit_card,
  sps_cardmonth      =>  $q->param('Expiration_Month_Card'),
  sps_cardyear          => $q->param('Expiration_Year'),
  sps_cardcvv           => $cvvValue, #$q->param('cvmvalue'),
  sps_cardname          => $q->param('Full_Name'),
  sps_street            => $q->param('Address_1'),
  sps_city              => $q->param('City'),
  sps_state             => $q->param('State'),
  sps_zip               => $q->param('Zip_Code'),
  sps_country           => $CountryID,
  sps_email             => $emailAddress,
  sps_ipaddress         => $remote_addr,
  ];
  my $res = $ua->request($req);
  if ($res->is_success) {
    my $content = $res->content;
    my $r = XMLin($content);
    my %resp = map { $_->{'KEY'}, $_->{'content'} } @{$r->{'FIELDS'}{'FIELD'}};
   open (FILE, ">/tmp/XLMTestOutpu");
     print FILE Dumper($r); 
     close(FILE);
                                                                                   
    if ($r->{transaction} and $r->{message} eq "Payment Successful") {
      # approved
      $log_in = $remote_addr.'-'.$r->{'transaction'};
      Add($paytot);
      #$error = "Sucess and the transaction is: ". $r->{transaction} . " Message: ". $r->{message};
      #Main();
      #exit;
    } else {
      
      #$error = "it gave an error: " . $r->{errormessage} . " $first: $last: :" . $q->param('Country') ;
      if ($r->{errormessage}){
        $error = 'An error occurred while attempting to authorize your credit card. Please try again. (err-ath)'  
      }
      $error = 'An error occurred while processing your card.  Error: '. $r->{errormessage};

      $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
      # Get the aes value from the db w/a select. Then use the val for the INSERT.
      my $enc_val_cc = Encrypt($credit_card, $ccEncryptString);

      $dbhS->do("replace into RateLimitCC set card = '" . $dbhS->quote($enc_val_cc) . "', last_use = NOW()") if $resp{'status'} == 2;
      send_deny_error('Paygea', $paytot, $r->{error}->{code}, $r->{errormessage}, $r->{transaction}, undef, undef, undef, undef, undef);
      #             ($gateway,      $paytot, $status,         $authcode,          $refnum,                   $avsres,           $cvvres,            $error,         $auth_response,         $fullresp, $bank_code)
      Main();
      exit;
    }
  } else {
    $error = "There has been a error with this process. Please try again. (err-axn)";
    Main();
    exit;
  }
}

sub pay_paygea_NEWAPI {
#CAMBILL
  my $paytot = shift;
if ($OrderType eq 'Cam_Order') { 
print $query->header(), "<html><head><title>Short Server Maintenance</title></head><body><h1>Server maintenance in progress - we'll be back in a moment </h1></body></html>";
exit;
}

  my ($CamAuth, $CamTotal);
  my $AllowCamOrder = 0;
  if ($OrderType eq 'Cam_Order'){
    my ($CamAuth, $CamTotal);
    $sth = $dbhS->prepare("select Authorized, Total from CamAuth where cc = aes_encrypt(" . $dbhS->quote($credit_card) . ",'$ccEncryptString')");
    if (!defined($sth) || !$sth->execute()) {die $q->header() . "\n\ngather the Authorized Cam Status " .  $dbhS->errstr . "<br>\n";}
    $sth->bind_columns(\$CamAuth, \$CamTotal);
    $sth->fetch();
    $sth->finish();
    if ((defined($CamAuth) && ($CamAuth == 1 || ($CamTotal + $paytot) < 500 )) || not(defined($CamAuth))){
      if (not(defined($CamAuth))) {
        # Get the aes value from the db w/a select. Then use the val for the INSERT.
        my $enc_val_cc = Encrypt($credit_card, $ccEncryptString);

               my $sqlstatement = "Insert into CamAuth values ('" . $dbhS->quote($enc_val_cc) . "', '". $q->param('Full_Name'). "', '". $q->param('Zip_Code'). "', 0, 0)";
               $dbhS->do($sqlstatement);
       }
    $AllowCamOrder = 1;

    }
  }
#END CAMBILL
if (($OrderType eq 'Cam_Order' and $AllowCamOrder == 1) || $OrderType ne 'Cam_Order'){
  my $billAmount = $paytot;
  $billAmount = $billAmount * 100;
  my $fullname = $q->param('Full_Name');
  $fullname =~ s/\s+/ /g;
  $fullname =~ s/^\s+//;
  $fullname =~ s/\s+$//;
  my $emailAddress = $q->param('Email');
  $emailAddress =~ s/^\s+//;
  my $CountryID = $countries_num{$q->param('Country')};
  my ($first, $last) = split(/\s/,$fullname);
  if ($last eq ''){ $last = $first;}
 
  my %cardtype;
  $cardtype{Mastercard} = 'MC';
  $cardtype{Visa} = 'VI';
  $cardtype{Discover} = 'DI';
  $cardtype{Amercan_Express} = 'AM';
  #Visa  => 'VI',
  #      Mastercard => 'MC',
  #      Discover => 'DI',
        #American Express => 'AM',
        #      );
  my $cardType;
  if ($q->param('CardName') eq 'American Express') {
        $cardType = 'American_Express';
  } else { 
    $cardType = $q->param('CardName');
  }
  my $zip = $q->param('Zip_Code');
  if ($zip eq ''){$zip = 'NA';}
  my $cardExp = $q->param('Expiration_Month_Card') . "/" . $q->param('Expiration_Year');
  my $req = POST 'https://realtime.paygea.com/servlet/DPServlet', [
  account               => $paygeaAccount,
  merchantId            => $paygeaID,
  merchantPwd           => $paygeaPW,
  merchantTxn           => $rande,
  amount                => $billAmount,
  custName1             => $first,
  custName2             => $last,
  cardNumber            => $credit_card,
  cardExp                => $cardExp,
  cvdIndicator          => "1",
  cvdValue              => $q->param('cvmvalue'),
  cardType              => $cardtype{$cardType},
  operation             => "P",
  clientVersion         => "1.1",
  #streetAddr            => $q->param('Address_1'),
  #city              => $q->param('City'),
  #province             => $q->param('State'),
  zip               => $zip, #$q->param('Zip_Code'),
  #country           => $q->param('Country'), # "US",#$CountryID,
  phone                 => '1111111111', 
  email             => $emailAddress,
  ];
  my $res = $ua->request($req);

  if ($res->is_success) {
    
    my $content = $res->content;
    my $m = new CGI($res->content());
    my $r_status     = $m->param('status');
    my $r_errCode     = $m->param('errCode');
    my $r_errString     = $m->param('errString');
    my $r_authCode      = $m->param('authCode');       
    my $r_avsInfo       = $m->param('avsInfo');
    my $r_cvdInfo       = $m->param('cvdInfo');
    my $r_amount        = $m->param('amount');
    my $r_txnNumber     = $m->param('txnNumber');
    my $r_subError      = $m->param('subError');
    my $r_subErrorString = $m->param('subErrorString');
    my $r_actionCode    = $m->param('actionCode');
    my $r_pmtError      = $m->param('pmtError');
    
                                                                                   
    if ($r_status eq "SP") {
      # approved
      $log_in = $remote_addr.'-'.$r_txnNumber;
      Add($paytot);
      #$error = "Sucess and the transaction is: ". $r_txnNumber . " Message: ". $r_authCode;;
      #Main();
      #exit;
    } else {
      
      #$error = "it gave an error: " . $r->{errormessage} . " $first: $last: :" . $q->param('Country') ;
      if ($r_pmtError eq "I"){
        $error = 'An error occurred while attempting to authorize your credit card. Please try again. (err-ath)'  
      }
      else {
        $error = 'An error occurred while processing your card.  Error: '. $r_errString;
        $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
        # Get the aes value from the db w/a select. Then use the val for the INSERT.
        my $enc_val_cc = Encrypt($credit_card, $ccEncryptString);

        $dbhS->do("replace into RateLimitCC set card = '" . $dbhS->quote($enc_val_cc) . "', last_use = NOW()") if $r_status eq "E";
        if ($q->param('Country') eq 'US' and $cc == 5) {
           send_deny_error('Paygea Sending to Merrick', $paytot, $r_errCode, $r_errString, $r_txnNumber, $r_avsInfo, $r_cvdInfo, $r_actionCode, $r_subErrorString, $r_authCode);
        } else {
           send_deny_error('Paygea', $paytot, $r_errCode, $r_errString, $r_txnNumber, $r_avsInfo, $r_cvdInfo, $r_actionCode, $r_subErrorString, $r_authCode);
        }
      
        #Reroute US based cards to Merrick.
        if ($q->param('Country') eq 'US' and $cc == 5) {
          pay_routemerrick($paytot);
        }
      }
      Main();
      exit;
    }
  } else {
    $error = "There has been a error with this process. Please try again. (err-axn)";
    Main();
    exit;
  }
#CAMBILL
     }
     else  {
       print $q->redirect('http://www.c4slive.com/AuthorizeCam.html');
     }
#CAMBILL
}



sub pay_paygea_DefaultSuncoast {
#CAMBILL
  my $paytot = shift;

# Is this store configured for a gateway?
  $sth = $dbh->prepare("
  select
  m.cc, m.descriptor, m.hold_percent,
  m.umkey,
  m.ePNAccount,
  m.goEMerch, m.goEPasswd,
  m.authNname, m.authNpasswd,
  m.linkPconfig, m.linkPkeyfile,
  m.capstoneID, m.capstonePasswd,
  m.paygeaID, m.paygeaPW, m.paygeaAccount,
  m.plugandpay
  from Merchant_Account m
  where m.cc = 5
  ");
$dbh = DBI->connect_cached($neildb::database, $neildb::dbadmin, $neildb::dbpasswd);
if (!defined($sth) || !$sth->execute()) {die $q->header() . "\n\n(select prodmerch) STH: " . ":: " . $dbh->errstr . "<br>\n";}
$sth->bind_columns(\$cc, \$descriptor, \$hold_percent, \$umkey, \$ePNAccount, \$goEMerch, \$goEPasswd, \$authNname, \$authNpasswd, \$linkPconfig, \$linkPkeyfile, \$cpstnID, \$cpstnPW, \$paygeaID, \$paygeaPW, \$paygeaAccount, \$plugandpay);
$sth->fetch();


  open LOG, ">> /home/OrderSystem/public_html/SecureProcess/SuncoastDefault.log";

if ($OrderType eq 'Cam_Order00') { 
print $query->header(), "<html><head><title>Short Server Maintenance</title></head><body><h1>Server maintenance in progress - we'll be back in a moment </h1></body></html>";
exit;
}

  my ($CamAuth, $CamTotal);
  my $AllowCamOrder = 0;
  if ($OrderType eq 'Cam_Order'){
    my ($CamAuth, $CamTotal);
    $sth = $dbhS->prepare("select Authorized, Total from CamAuth where cc = aes_encrypt(" . $dbhS->quote($credit_card) . ",'$ccEncryptString')");
    if (!defined($sth) || !$sth->execute()) {die $q->header() . "\n\ngather the Authorized Cam Status " .  $dbhS->errstr . "<br>\n";}
    $sth->bind_columns(\$CamAuth, \$CamTotal);
    $sth->fetch();
    $sth->finish();
    if ((defined($CamAuth) && ($CamAuth == 1 || ($CamTotal + $paytot) < 500 )) || not(defined($CamAuth))){
       if (not(defined($CamAuth))) {
          # Get the aes value from the db w/a select. Then use the val for the INSERT.
          my $enc_val_cc = Encrypt($credit_card, $ccEncryptString);
    
          my $sqlstatement = "Insert into CamAuth values ('$enc_val_cc', '". $q->param('Full_Name'). "', '". $q->param('Zip_Code'). "', 0, 0)";
               $dbhS->do($sqlstatement);
       }
    $AllowCamOrder = 1;

    }
  }
#END CAMBILL
if (($OrderType eq 'Cam_Order' and $AllowCamOrder == 1) || $OrderType ne 'Cam_Order'){
  my $billAmount = $paytot;
  $billAmount = $billAmount * 100;
  my $fullname = $q->param('Full_Name');
  $fullname =~ s/\s+/ /g;
  $fullname =~ s/^\s+//;
  $fullname =~ s/\s+$//;
  my $emailAddress = $q->param('Email');
  $emailAddress =~ s/^\s+//;
  my $CountryID = $countries_num{$q->param('Country')};
  my ($first, $last) = split(/\s/,$fullname);
  if ($last eq ''){ $last = $first;}
 
  my %cardtype;
  $cardtype{Mastercard} = 'MC';
  $cardtype{Visa} = 'VI';
  $cardtype{Discover} = 'DI';
  $cardtype{Amercan_Express} = 'AM';
  #Visa  => 'VI',
  #      Mastercard => 'MC',
  #      Discover => 'DI',
        #American Express => 'AM',
        #      );
  my $cardType;
  if ($q->param('CardName') eq 'American Express') {
        $cardType = 'American_Express';
  } else { 
    $cardType = $q->param('CardName');
  }
  my $zip = $q->param('Zip_Code');
  if ($zip eq ''){$zip = 'NA';}
  my $cardExp = $q->param('Expiration_Month_Card') . "/" . $q->param('Expiration_Year');
  my $req = POST 'https://realtime.paygea.com/servlet/DPServlet', [
  account               => $paygeaAccount,
  merchantId            => $paygeaID,
  merchantPwd           => $paygeaPW,
  merchantTxn           => $rande,
  amount                => $billAmount,
  custName1             => $first,
  custName2             => $last,
  cardNumber            => $credit_card,
  cardExp                => $cardExp,
  cvdIndicator          => "1",
  cvdValue              => $q->param('cvmvalue'),
  cardType              => $cardtype{$cardType},
  operation             => "P",
  clientVersion         => "1.1",
  #streetAddr            => $q->param('Address_1'),
  #city              => $q->param('City'),
  #province             => $q->param('State'),
  zip               => $zip, #$q->param('Zip_Code'),
  #country           => $q->param('Country'), # "US",#$CountryID,
  phone                 => '1111111111', 
  email             => $emailAddress,
  ];
  my $res = $ua->request($req);

  if ($res->is_success) {
    
    my $content = $res->content;
    my $m = new CGI($res->content());
    my $r_status     = $m->param('status');
    my $r_errCode     = $m->param('errCode');
    my $r_errString     = $m->param('errString');
    my $r_authCode      = $m->param('authCode');       
    my $r_avsInfo       = $m->param('avsInfo');
    my $r_cvdInfo       = $m->param('cvdInfo');
    my $r_amount        = $m->param('amount');
    my $r_txnNumber     = $m->param('txnNumber');
    my $r_subError      = $m->param('subError');
    my $r_subErrorString = $m->param('subErrorString');
    my $r_actionCode    = $m->param('actionCode');
    my $r_pmtError      = $m->param('pmtError');
    
                                                                                   
    if ($r_status eq "SP") {
      # approved
  print LOG scalar localtime;
  print LOG "\n Order APPROVED\n";
  close(LOG);

      $log_in = $remote_addr.'-'.$r_txnNumber;
      Add($paytot);
      #$error = "Sucess and the transaction is: ". $r_txnNumber . " Message: ". $r_authCode;;
      #Main();
      #exit;
    } else {
      
      #$error = "it gave an error: " . $r->{errormessage} . " $first: $last: :" . $q->param('Country') ;
      if ($r_pmtError eq "I"){
        $error = 'An error occurred while attempting to authorize your credit card. Please try again. (err-ath)'  
      }
      else {
        $error = 'An error occurred while processing your card.  Error: '. $r_errString;
        $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
        
        my $enc_val_cc = Encrypt($credit_card, $ccEncryptString);
        $dbhS->do("replace into RateLimitCC set card = " . $dbhS->quote($enc_val_cc) . ", last_use = NOW()") if $r_status eq "E";
        send_deny_error('Sent To Suncoast, Still failed', $paytot, $r_errCode, $r_errString, $r_txnNumber, $r_avsInfo, $r_cvdInfo, $r_actionCode, $r_subErrorString, $r_authCode);
  print LOG scalar localtime;
  print LOG "\n Order DENIED\n";
      }
  close(LOG);
      Main();
      exit;
    }
  } else {
    $error = "There has been a error with this process. Please try again. (err-axn)";
    Main();
    exit;
  }
#CAMBILL
     }
     else  {
       print $q->redirect('http://www.c4slive.com/AuthorizeCam.html');
     }
#CAMBILL
}



sub pay_linkPoint {
  my $paytot = shift;
  # note that standard Business::OnlinePayment::LinkPoint module was modified - ensure correct copy installed!
  my $gtot = sprintf "%.2f", $paytot;
  my $tx = new Business::OnlinePayment( 'LinkPoint',
    'storename' => $linkPconfig,
    'keyfile'   => $linkPkeyfile,
  );

  $tx->content(
    type           => $q->param('CardName'),
    action         => 'Normal Authorization',
    amount         => $gtot,
    invoice_number => $rande,
    name           => $q->param('Full_Name'),
    address        => $q->param('Address_1'),
    city           => $q->param('City'),
    state          => $q->param('State'),
    zip            => $q->param('Zip_Code'),
    email          => $q->param('Email'),
    card_number    => $credit_card,
    expiration     => $q->param('Expiration_Month_Card').$q->param('Expiration_Year'),
    cvv2           => $q->param('cvmvalue'),
    ip             => $remote_addr,
  );

  use Data::Dump qw(dump);
  open LPT, ">> /home/OrderSystem/public_html/SecureProcess/linkpt.log";
  print LPT "\n\nPre-submit:\n", dump $tx;

  $tx->submit();

  print LPT "\nPost-submit:\n",dump $tx;
  close LPT;

  if($tx->is_success()) {
    $log_in = $remote_addr.'-'.$tx->authorization;
    Add($paytot);
  } else {
    $error = 'Your credit card has been denied, or an error occurred. (err-azq)';
    $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
    # Get the aes value from the db w/a select. Then use the val for the INSERT.
    my $enc_val_cc = Encrypt($credit_card, $ccEncryptString);
    
    $dbhS->do("replace into RateLimitCC set card = " . $dbhS->quote($enc_val_cc) . ", last_use = NOW()");
    send_deny_error('LinkPoint', $paytot, $tx->result_text, $tx->result_code, undef,   $tx->avs_code, undef,   $tx->error_message, $tx->message,   undef);
    #              ($gateway,    $paytot, $status,          $authcode,        $refnum, $avsres,       $cvvres, $error,             $auth_response, $fullresp, $bank_code)
    Main();
    exit;
  }
}

sub pay_authorizeNet {
  my $paytot = shift;
  # Business::OnlinePayment::LinkPoint used as is, latest lpperl.pm installed
  my $gtot = sprintf "%.2f", $paytot;
  my $tx = new Business::OnlinePayment('AuthorizeNet');

  $tx->content(
    type           => $q->param('CardName'),
    login          => $authNname,
    password       => $authNpasswd,
    action         => 'Normal Authorization',
    amount         => $gtot,
    invoice_number => $rande,
    first_name     => $q->param('First_Name'),
    last_name      => $q->param('Last_Name'),
    address        => $q->param('Address_1'),
    city           => $q->param('City'),
    state          => $q->param('State'),
    zip            => $q->param('Zip_Code'),
    email          => $q->param('Email'),
    card_number    => $credit_card,
    expiration     => $q->param('Expiration_Month_Card').$q->param('Expiration_Year'),
    cvv2           => $q->param('cvmvalue'),
    customer_ip    => $remote_addr,
  );
  $tx->submit();

  if($tx->is_success()) {
    $log_in = $remote_addr.'-'.$tx->authorization;
    Add($paytot);
  } else {
    $error = 'Your credit card has been denied, or an error occurred. (err-bbt)';
    $dbhS = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
    
    # Get the aes value from the db w/a select. Then use the val for the INSERT.
    my $enc_val_cc = Encrypt($credit_card, $ccEncryptString);
      
    $dbhS->do("replace into RateLimitCC set card = '" . $dbhS->quote($enc_val_cc) . "', last_use = NOW()");
    send_deny_error('AuthorizeNet', $paytot, $tx->result_code, $tx->result_code, $tx->order_number, $tx->avs_code, $tx->cvv2_response, $tx->error_message, undef,          undef);
    #              ($gateway,       $paytot, $status,          $authcode,        $refnum,           $avsres,       $cvvres,            $error,             $auth_response, $fullresp, $bank_code)
    Main();
    exit;
  }
}

sub pay_gizmo {
  my $paytot = shift;
  # 1st check all 3 values
  if (!($q->param('gizmo_username') and $q->param('gizmo_password') and $q->param('gizmo_email'))) {
    $error = "Username, Password, and Email are all required for Gizmo Card payment (err-bdw)\n";
    Main();
    exit;
  }
  my $req = POST 'https://secure.gizmocard.com/gw/withdrawal.cgi', [
    username => $q->param('gizmo_username'),   # Customer's Gizmo Card Username
    password => $q->param('gizmo_password'),   # Customer's Gizmo Card Password
    email    => $q->param('gizmo_email'),      # Customer's Gizmo email address
    amount   => $paytot,                       # Amount to charge customer
    url      => $q->self_url,                  # URL of the page that this is coming from
    ip       => $remote_addr,                  # IP of the customer
    refer    => $q->referer(),                 # Referer. Not really that important
    product  => $the_domain,           # The product that is being sold
  ];
  $req->authorization_basic('clips4sale', 'huge68');
  my $res = $ua->request($req);
  if ($res->is_success) {
    my $k = CGI->new($res->content());
    if ($k->param('accepted')) {
      $log_in = $remote_addr.'-'.$k->param('transaction_id');
      Add($paytot);
    } else {
      $error = $k->param('error') . " " . $k->param('Mess');
      Main();
      exit;
    }
  } else {
    $error = "There has been a error with this process. Please try again." .$res->decoded_content;
    Main();
    exit;
  }
}

sub pay_clipcash {



  my $paytot = shift;
  if (!($q->param('clipcash_number') and $q->param('clipcash_email') and $q->param('clipcash_name'))) {
     $error = "Clip Cash Number, Email, and Name are all required for Clip Cash Card payment (err-ccs)\n";
     Main();
     exit;
  }
  $ua = LWP::UserAgent->new();
  my $clipcashnumber = $q->param('clipcash_number');
  $clipcashnumber =~ s/\s//g;
  my $req = POST 'https://secure.clipcash.com/gw/withdrawal.cgi',
        [
             card_no         => $clipcashnumber,
             email           => $q->param('clipcash_email'),
             amount          => $paytot,
             url             => $q->self_url,
             ip              => $remote_addr,
             refer           => $q->referer(),
             product         => $the_domain
        ];
  $req->authorization_basic('clips4sale', 'huge68');
  my $res = $ua->request($req);
  if ($res->is_success) {
     my $k = CGI->new($res->content());
     if ($k->param('accepted')) {
         $log_in = $remote_addr.'-'.$k->param('transaction_id');
         Add($paytot);
     } else {
         $error = $k->param('error') . " " . $k->param('Mess') . "<br> <a href=\"https://secure.clipcash.com/asignup.cgi\" target=\"top\">Click Here</a> to activate or create your account";
         Main();
         exit;
     }
  } else {
    $error = "There has been a error with this process. Please try again.";
    Main();
    exit;
  } 
}
  
sub get_video_html {
  my ($fullname, $descriptor, $grand_total, $pemail, $log_in, $sorder, $customer_email) = @_;
  return <<_EOF_;
<table border="0" align="center" valign="middle">
    <tr>
    <td align="center">
        <h3><font color="red">Do not refresh this page or you will get double billed</font></h3>
        <h4><font color="red">You might not receive your confirmation email if you are using a free email account. Please print this page out for your records in case of a problem.</font></h4>
    </td>
  </tr>
  <tr>
    <td>
      Dear $fullname,<br>
      <br>
      Your order has been discreetly billed by <b>$descriptor</b> in the amount of \$$grand_total<br>
      Please print this page for your records.<br><br>
      Video ID#:     $log_in<br>
      Sales Order#: $sorder<br>
      Tracking Number: $customer_id-$sorder<br>
      <br>
      Video(s) you have ordered:<br>
      $customer_email<br>
      <br>
      If you have any questions or changes regarding shipping, or any problems with your videos, email $pemail.<br>
      <br>
      If you have any questions or problems with billing, email <a href="mailto:info\@videos4sale.com">info\@videos4sale.com</a> or call 1-877-312-8559 (Outside the US, please call 727-498-8515)<br>
    </td>
  </tr>
</table>


<script language="JavaScript" Type="text/javascript">
<!-- Yahoo! Inc.
window.ysm_customData = new Object();
window.ysm_customData.conversion = "transid=,currency=,amount=";
var ysm_accountid = "1S3INORNOO83TH9LBBMKVF6BKO0";
document.write("<SCR" + "IPT language='JavaScript' type='text/javascript' "
+ "SRC=//" + "srv2.wa.marketingsolutions.yahoo.com" + "/script/ScriptServlet" + "?aid=" + ysm_accountid
+ "></SCR" + "IPT>");
//-->
</script>

<!-- Start of DoubleClick Spotlight Tag: Please do not remove-->
<!-- Activity Name for this tag is:Conversion Secure -->
<!-- Web site URL where tag should be placed: http://http://www.clips4sale.com/conversion -->
<!-- This tag must be placed within the opening <body> tag, as close to the beginning of it as possible-->
<!-- Creation Date:1/8/2009 -->
<SCRIPT language="JavaScript">
var axel = Math.random()+"";
var a = axel * 10000000000000;
document.write('<IMG SRC="https://ad.doubleclick.net/activity;src=2158808;type=conve399;cat=conve519;ord=1;num='+ a + '?" WIDTH=1 HEIGHT=1 BORDER=0>');
</SCRIPT>
<NOSCRIPT>
<IMG SRC="https://ad.doubleclick.net/activity;src=2158808;type=conve399;cat=conve519;ord=1;num=1?" WIDTH=1 HEIGHT=1 BORDER=0>
</NOSCRIPT>
<!-- End of DoubleClick Spotlight Tag: Please do not remove-->


_EOF_
}

sub get_clip_html {
  #removed abcsearch traffic monitor
  ##<script language=javascript
  #src="https://admin.abcsearch.com/af/saletrack.pl?username=PRIMECLIPS">
  #</script>
  my $ProducerTrackingCode = '';
  my $dbhSTPD= DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
  my $sthTPD = $dbhSTPD->prepare("select TrackingCode from StudioTrackingData where ProducerID = '" . $q->param('storeid') . "' and Active = 1");
  if (!defined($sthTPD) || !$sthTPD->execute()) {print "\n(select clip from clips) STH: " . $dbhSTPD->errstr . "<br>\n"; die;}
  while (my $row_ref = $sthTPD->fetchrow_hashref()) {
          $ProducerTrackingCode .= $row_ref->{'TrackingCode'};
  };
        $sthTPD->finish;
  $dbhSTPD->disconnect;
  
  my ($fullname, $log_in, $the_domain, $pay_meth_text, $sorder) = @_;
  

return <<_EOF_;
<table border="0" align="center" valign="middle">
    <tr>
    <td align="center">
        <h3><font color="red">Do not refresh this page or you will get double billed</font></h3>
        <h4><font color="red">You might not receive your confirmation email if you are using a free email account. Please print this page out for your records in case of a problem.  You must have your SO# or Clip ID# handy when contacting customer support.</font></h4>
    </td>
  </tr>
  <tr>
    <td align="center">
        Below is your Clip ID Number.<br>
        Clip ID#: <b>$log_in</b><br>
        Here is the url to download your clips now.<br>
        You Have 48Hrs to download your clips.<br>
<a href="http://www.$the_domain/?do=checkOrder&Username=$log_in" target="_gizmo">http://www.$the_domain/?do=checkOrder</a>
    </td>
  </tr>
  <tr>
    <td>
      Dear $fullname,<br>
      <br>
      $pay_meth_text<br>
      Please print this page for your records.<br>
      Sales Order#: $sorder<br>
      If you have any questions or problems with billing and or your downloadable clips, email <a href="mailto:info\@$the_domain">info\@$the_domain</a> or call 1-877-312-8559 (Outside the US, please call 727-498-8515)<br>
  <br><br>
  <img src="/images/Phone2.gif"><br>
    </td>
  </tr>
</table>


<script language="JavaScript" Type="text/javascript">
<!-- Yahoo! Inc.
window.ysm_customData = new Object();
window.ysm_customData.conversion = "transid=,currency=,amount=";
var ysm_accountid = "1S3INORNOO83TH9LBBMKVF6BKO0";
document.write("<SCR" + "IPT language='JavaScript' type='text/javascript' "
+ "SRC=//" + "srv2.wa.marketingsolutions.yahoo.com" + "/script/ScriptServlet" + "?aid=" + ysm_accountid
+ "></SCR" + "IPT>";
//-->
</script>

<!-- Start of DoubleClick Spotlight Tag: Please do not remove-->
<!-- Activity Name for this tag is:Conversion Secure -->
<!-- Web site URL where tag should be placed: http://http://www.clips4sale.com/conversion -->
<!-- This tag must be placed within the opening <body> tag, as close to the beginning of it as possible-->
<!-- Creation Date:1/8/2009 -->
<SCRIPT language="JavaScript">
var axel = Math.random()+"";
var a = axel * 10000000000000;
document.write('<IMG SRC="https://ad.doubleclick.net/activity;src=2158808;type=conve399;cat=conve519;ord=1;num='+ a + '?" WIDTH=1 HEIGHT=1 BORDER=0>');
</SCRIPT>
<NOSCRIPT>
<IMG SRC="https://ad.doubleclick.net/activity;src=2158808;type=conve399;cat=conve519;ord=1;num=1?" WIDTH=1 HEIGHT=1 BORDER=0>
</NOSCRIPT>
<!-- End of DoubleClick Spotlight Tag: Please do not remove-->

<!-- begin Black Label Ads, Purchases/sales tracking -->
<img border="0" hspace="0" vspace="0" width="1" height="1" src="http://stats.adbrite.com/stats/stats.gif?_uid=596483&_pid=0" />
<!-- end Black Label Ads, Purchases/sales tracking -->

<!-- <img src="/gaecom.php?t=UA-6689296-1&d=$domain&CampaignCode=$CampaignCode&storeid=$storeid&referer=$referrer&orderid=$sorder" alt="GA" /> -->

<!-- Johathan's conversion code -->
<!-- Google Code for Sale Conversion Page -->
 <script language="JavaScript" type="text/javascript">
 <!--
 var google_conversion_id = 1050368591;
 var google_conversion_language = "en_US";
 var google_conversion_format = "1";
 var google_conversion_color = "ffffff";
 var google_conversion_label = "gOfDCJWbgAEQz7Tt9AM";
 //-->
 </script>
 <script language="JavaScript"
 src="http://www.googleadservices.com/pagead/conversion.js">
 </script>
 <noscript>
 <img height="1" width="1" border="0" 
  src="http://www.googleadservices.com/pagead/conversion/1050368591/?label=gOfDCJWbgAEQz7Tt9AM&amp;guid=ON&amp;script=0"/>
 </noscript>

<!-- Google Code for Sales Conversion Page -->
<script type="text/javascript">
/* <![CDATA[ */
var google_conversion_id = 978525299;
var google_conversion_language = "en";
var google_conversion_format = "3";
var google_conversion_color = "ffffff";
var google_conversion_label = "8nA9COWWywIQ87jM0gM";
var google_conversion_value = 0;
/* ]]> */
</script>
<script type="text/javascript" src="https://www.googleadservices.com/pagead/conversion.js">
</script>
<noscript>
<div style="display:inline;">
<img height="1" width="1" style="border-style:none;" alt="" src="https://www.googleadservices.com/pagead/conversion/978525299/?label=8nA9COWWywIQ87jM0gM&amp;guid=ON&amp;script=0"/>
</div>
</noscript>


<img src="http://4148ue1f0zwu0903.marinsm.com/tp?cid=4148ue1f0zwu0903&trans=UTM:T|orderid||revenue|||||" width="1" height="1">
<img src="http://tracking.admarketplace.net/tracking?pid=1414&fc=1&cid=3900&eventid=0&orderval=0.00&v=2&orderid=&custominfo=" width="1" height="1" border="0"/>

 <iframe frameborder="0" scrolling="no" marginheight="0px" marginwidth="0px" name="CilpsCC" id="ClipsCC" src="https://secure.clips4sale.com/clearCart.php?storeID=$storeid" height="1" width="1"></iframe>

$ProducerTrackingCode

_EOF_
}

sub get_image_html {
  my ($fullname, $log_in, $the_domain, $pay_meth_text, $sorder) = @_;
  return <<_EOF_;
<table border="0" align="center" valign="middle">
    <tr>
    <td align="center">
        <h3><font color="red">Do not refresh this page or you will get double billed</font></h3>
        <h4><font color="red">You might not receive your confirmation email if you are using a free email account. Please print this page out for your records in case of a problem.  You must have your SO# or Image ID# handy when contacting customer support.</font></h4>
    </td>
  </tr>
  <tr>
    <td align="center">
        Below is your Image ID Number.<br>
        Image ID#: <b>$log_in</b><br>
        Here is the url to download your images now.<br>
        You Have 48Hrs to download your images.<br>
        <a href="http://www.$the_domain/?do=checkOrder&Username=$log_in" target="_gizmo">http://www.$the_domain/?do=checkOrder</a>
    </td>
  </tr>
  <tr>
    <td>
      Dear $fullname,<br>
      <br>
      $pay_meth_text<br>
      Please print this page for your records.<br>
      Sales Order#: $sorder<br>
      If you have any questions or problems with billing and or your downloadable images, email <a href="mailto:info\@$the_domain">info\@$the_domain</a> or call 1-877-312-8559 (Outside the US, please call 727-498-8515)<br>
    </td>
  </tr>
</table>


<script language="JavaScript" Type="text/javascript">
<!-- Yahoo! Inc.
window.ysm_customData = new Object();
window.ysm_customData.conversion = "transid=,currency=,amount=";
var ysm_accountid = "1S3INORNOO83TH9LBBMKVF6BKO0";
document.write("<SCR" + "IPT language='JavaScript' type='text/javascript' "
+ "SRC=//" + "srv2.wa.marketingsolutions.yahoo.com" + "/script/ScriptServlet" + "?aid=" + ysm_accountid
+ "></SCR" + "IPT>";
//-->
</script>


_EOF_
}

sub get_cust_vid_email {
  my ($fullname, $log_in, $sorder, $grand_total, $descriptor, $customer_email, $pemail, $address, $city, $state, $zipcode, $country, $vidformats) = @_;
  return <<_EOF_;
Dear $fullname,

Thank you for your order.

Video ID#:    $log_in
Sales Order#: $sorder
$vidformats
Tracking Number: $customer_id-$sorder
Your credit card was billed \$$grand_total from $descriptor

Video(s) you have ordered:
$customer_email

If you have any questions or problems with your videos, email $pemail.

If you do not receive your videos within 15 days, 21 days for International orders, call the hosting company at  1-877-312-8559. (Outside the US, please call 727-498-8515)

_EOF_
}
#$fullname
#$address
#$city, $state  $zipcode
#$country
#_EOF_
#}

sub get_cust_clip_email {
  my ($fullname, $log_in, $sorder, $pay_meth_text, $customer_email, $the_domain, $pemail, $address, $city, $state, $zipcode, $country) = @_;
  return <<_EOF_;
Dear $fullname,

Thank you for your order.

Clip ID#:     $log_in
Sales Order#: $sorder
$pay_meth_text

Clip(s) you have ordered:
$customer_email

To download your clips either click the url below or copy and paste the entire url into
your browser and then enter your CLIP ID#.

http://www.$the_domain/?do=cLogin

CLIP ID#: $log_in

You can also click the url below or copy and paste the entire url into your web
browser.

URL: http://www.$the_domain/?do=checkOrder&Username=$log_in

You have 48Hrs to download your clips.

If you would like to contact the webmaster about their clips. You can email them at $pemail

If you have any questions or problems with your clips, email info\@$the_domain or call  1-877-312-8559 (Outside the US, please call 727-498-8515)
$RadioHTML
_EOF_
}
#$fullname
#$city, $state  $zipcode
#$country
#_EOF_
#}

sub get_cust_image_email {
  my ($fullname, $log_in, $sorder, $pay_meth_text, $customer_email, $the_domain, $pemail, $address, $city, $state, $zipcode, $country) = @_;
  return <<_EOF_;
Dear $fullname,

Thank you for your order.

Image ID#:    $log_in
Sales Order#: $sorder
$pay_meth_text

Image(s) you have ordered:
$customer_email

To download your images either click the url below or copy and paste the entire url into
your browser and then enter your IMAGE ID#.

http://www.$the_domain/?do=cLogin

IMAGE ID#: $log_in

You can also click the url below or copy and paste the entire url into your web
browser.

URL: http://www.$the_domain/?do=checkOrder&Username=$log_in

You have 48Hrs to download your images.

If you would like to contact the webmaster about their images. You can email them at $pemail

If you have any questions or problems with your images, email info\@$the_domain or call  1-877-312-8559 (Outside the US, please call 727-498-8515)
_EOF_
}
#$fullname
#$city, $state  $zipcode
#$country
#_EOF_
#}

sub get_prod_vid_email {
  my ($storeid, $sorder, $vendor_email, $shipping, $totalamount, $vendorcommission, $customer_id, $log_in, $fullname, $email, $address, $city, $state, $zipcode, $country, $ccfs_html, $vidformats) = @_;
  return <<_EOF_;
<p>
Store ID: $storeid<br>
SO# $sorder<br>
</p>
<table>
$vendor_email
<tr><td>Shipping & Handling</td><td>\$$shipping</td></tr>
<tr><td>Totals</td><td>\$$totalamount</td><td>\$$vendorcommission</td></tr>
</table>
<p>
Customer#: $customer_id<br>
Video ID#: $log_in<br>
$vidformats<br>
Name: $fullname<br>
EMail: $email<br> 
</p>
<p>
$fullname<br>
$address
$city, $state  $zipcode<br>
$country<br>
</p>
<p>
$ccfs_html
</p>
_EOF_
# EMail: $email<br> was removed
#
}

sub get_prod_pack_email {
  my ($storeid, $sorder, $vendor_pack_email, $shipping, $totalamount, $customer_id, $log_in, $fullname, $email, $address, $city, $state, $zipcode, $country, $vidformats) = @_;
  return <<_EOF_;
<p>
Store ID: $storeid<br>
SO# $sorder<br>
</p>
<table>
$vendor_pack_email
<tr><td>Shipping & Handling</td><td>\$$shipping</td></tr>
<tr><td>Totals</td><td>\$$totalamount</td></tr>
</table>
<p>
Customer#: $customer_id<br>
Video ID#: $log_in<br>
$vidformats<br>
Name: $fullname<br>
</p>
<p>
$fullname<br>
$address<br>
$city, $state  $zipcode<br>
$country<br>
</p>
_EOF_
}

sub get_prod_clip_email {
  my ($storeid, $sorder, $log_in, $vendor_email, $totalamount, $vendorcommission, $remote_addr, $remote_country, $customer_id, $fullname, $email, $city, $state, $country, $ccfs_html) = @_;
  my ($left,$right) = split(/ /,$fullname);
  my $FirstLetterFirst = substr($left,0,1);
  my $FirstLetterLast = substr($right,0,1);
  return <<_EOF_;
<p>
Store ID: $storeid<br>
SO# $sorder<br>
Clip ID#: $log_in<br>
</p>
<table>
$vendor_email
<tr><td>Totals</td><td>\$$totalamount</td><td>\$$vendorcommission</td></tr>
</table>
<p>
IP: $remote_addr<br>
Country from IP: $remote_country<br>
</p>
<p>
Customer#: $customer_id<br>
</p>
<p>
$FirstLetterFirst $FirstLetterLast<br>
$city, $state <br>
$country<br>

</p>

<p>
$ccfs_html
</p>
_EOF_
}

sub get_prod_image_email {
  my ($storeid, $sorder, $log_in, $vendor_email, $totalamount, $vendorcommission, $remote_addr, $remote_country, $customer_id, $fullname, $email, $city, $state, $country, $ccfs_html) = @_;
  my ($left,$right) = split(/ /,$fullname);
  my $FirstLetterFirst = substr($left,0,1);
  my $FirstLetterLast = substr($right,0,1);
  return <<_EOF_;
<p>
Store ID: $storeid<br>
SO# $sorder<br>
Image ID#: $log_in<br>
</p>
<table>
$vendor_email
<tr><td>Totals</td><td>\$$totalamount</td><td>\$$vendorcommission</td></tr>
</table>
<p>
IP: $remote_addr<br>
Country from IP: $remote_country<br>
</p>
<p>
Customer#: $customer_id<br>
$FirstLetterFirst $FirstLetterLast<br>
$city, $state <br>
$country<br>
<p>

$ccfs_html
</p>
_EOF_
}

sub get_neil_vid_email {
  my ($storeid, $sorder, $admin_email, $shipping, $totalamount, $vendorcommission, $tneilmon, $customer_id, $log_in, $email, $credit_card, $remote_addr, $fullname, $address, $city, $state, $zipcode, $country, $ccfs_html, $vidformats) = @_;
  return <<_EOF_;
<p>
Store ID: $storeid<br>
SO# $sorder<br>
</p>
<table>
$admin_email
<tr><td>Shipping & Handling</td><td>\$$shipping</td></tr>
<tr><td>Totals:</td><td>\$$totalamount</td><td>\$$vendorcommission</td><td>$tneilmon</td></tr>
</table>
<p>
Customer#: $customer_id<br>
Video ID#: $log_in<br>
$vidformats<br>
EMail: $email<br>
</p>
<p>
IP: $remote_addr<br>
</p>
<p>
$fullname<br>
$address<br>
$city, $state  $zipcode<br>
$country<br>
</p>
<p>
$ccfs_html
</p>
_EOF_
}

sub get_neil_clip_email {
  my ($storeid, $sorder, $admin_email, $totalamount, $vendorcommission, $tneilmon, $descriptor, $customer_id, $log_in, $email, $pass, $remote_addr, $remote_country, $fullname, $address, $city, $state, $zipcode, $country, $ccfs_html) = @_;
  return <<_EOF_;
<p>
Store ID: $storeid<br>
SO# $sorder<br>
</p>
<table>
$admin_email
<tr><td>Totals:</td><td>\$$totalamount</td><td>\$$vendorcommission</td><td>$tneilmon</td></tr>
</table>
<p>
Customer#: $descriptor $customer_id<br>
Clip ID#: $log_in<br>
EMail: $email<br>
</p>
<p>
CC: pass<br>
IP: $remote_addr<br>
Country from IP: $remote_country<br>
</p>
<p>
$fullname<br>
$address<br>
$city, $state  $zipcode<br>
$country<br>
</p>
<p>
$ccfs_html
</p>
_EOF_
}

sub get_neil_cam_email {
  my ($storeid, $sorder, $admin_email, $totalamount, $vendorcommission, $tneilmon, $descriptor, $customer_id, $log_in, $email, $pass, $remote_addr, $remote_country, $fullname, $address, $city, $state, $zipcode, $country, $ccfs_html, $transID) = @_;
  return <<_EOF_;
<p>
Store ID: $storeid<br>
SO# $sorder<br>
</p>
<table>
$admin_email
<tr><td>Totals:</td><td>\$$totalamount</td><td>\$$vendorcommission</td><td>$tneilmon</td></tr>
</table>
<p>
Customer#: $descriptor $customer_id<br>
Cam/Member order Transaction ID: $transID<br>
EMail: $email<br>
</p>
<p>
IP: $remote_addr<br>
Country from IP: $remote_country<br>
</p>
<p>
$fullname<br>
$address<br>
$city, $state  $zipcode<br>
$country<br>
</p>
<p>
$ccfs_html
</p>
_EOF_
}


sub get_neil_image_email {
  my ($storeid, $sorder, $admin_email, $totalamount, $vendorcommission, $tneilmon, $descriptor, $customer_id, $log_in, $email, $pass, $remote_addr, $remote_country, $fullname, $address, $city, $state, $zipcode, $country, $ccfs_html) = @_;
  return <<_EOF_;
<p>
Store ID: $storeid<br>
SO# $sorder<br>
</p>
<table>
$admin_email
<tr><td>Totals:</td><td>\$$totalamount</td><td>\$$vendorcommission</td><td>$tneilmon</td></tr>
</table>
<p>
Customer#: $descriptor $customer_id<br>
Image ID#: $log_in<br>
EMail: $email<br>
</p>
<p>
CC: pass<br>
IP: $remote_addr<br>
Country from IP: $remote_country<br>
</p>
<p>
$fullname<br>
$address<br>
$city, $state  $zipcode<br>
$country<br>
</p>
<p>
$ccfs_html
</p>
_EOF_
}



sub Encrypt
{
  my $enc = "ERROR";
  my $val = shift;
  my $enckey = shift;
  
  my $dbz = DBI->connect_cached($securedb::database, $securedb::dbadmin, $securedb::dbpasswd);
  my $dbval = $dbz->selectrow_array("SELECT aes_encrypt(". $dbz->quote($val) .",'$enckey') AS enc");
  if(defined($dbval)) {
    $enc = $dbval;
  }
  
  return $enc;
}
sub TranslateHeadings {


  my $lang = $q->param('Lang');
  my %languages =( 
      'de' => 'de_DE',
      'fr' => 'fr_FR'
  ) ; 
  my $Lang = $languages{$lang};
  $template->param(LANG => $lang);

    setlocale(LC_MESSAGES, "$Lang");
    my $d = Locale::gettext->domain("checkout");
    $d->dir("/home/OrderSystem/locale");
    bindtextdomain("checkout", "/home/OrderSystem/locale");
  
  $template->param(BI1 => $d->get('Browser Information'));

  $template->param(BI3 => $d->get('Host'));
  $template->param(BI4 => $d->get('IP Address'));
  $template->param(BI5 => $d->get('Country'));
  $template->param(BI6 => $d->get('Browser'));

  $template->param(OD1 => $d->get('Order Details'));
  $template->param(OD2 => $d->get('Clips'));
  $template->param(OD3 => $d->get('Images'));
  $template->param(OD4 => $d->get('Video'));
  $template->param(OD5 => $d->get('Format'));
  $template->param(OD6 => $d->get('Price'));

  #Needs to be in loop itemlist
  # $template->param(OD7 => $d->get('You have previously ordered the title below'));
  
$template->param(directebanking => $DEBurl);
$template->param(clipcashredirect => $CCurl);
#my $tempCCurl = 'http://www.clipcash.com';
#$template->param(clipcashredirect => $tempCCurl);

  $template->param(SHIPPING => $d->get('Shipping'));
  $template->param(TOTAL => $d->get('Total'));
  $template->param(CCAS => $d->get('Your Credit Card Bill will appear as'));
  $template->param(PAYMETH => $d->get('Payment Method'));
  $template->param(SELPAYMETH => $d->get('Select Payment Method'));

  $template->param(CCM1 => $d->get('Credit Card'));
  $template->param(CLIPCASH => $d->get('ClipCash'));
  $template->param(WICLIPCASH => $d->get("What's a Clip Cash Card?"));
  $template->param(GIZMO => $d->get('Gizmo Card'));
  $template->param(WIGIZMO => $d->get("What's a Gizmo Card?"));
  $template->param(INFO => $d->get("Information"));
  $template->param(REQFIELD => $d->get('Required Fields'));
  $template->param(TNAME => $d->get('Name'));
  $template->param(FNAME => $d->get('First Name'));
  $template->param(LNAME => $d->get('Last Name'));
  $template->param(STADD => $d->get('Street Address'));
  $template->param(CITYP => $d->get('City'));
  $template->param(STATEP => $d->get('State/Province'));
  $template->param(ZIPT => $d->get('Zip Code'));
  $template->param(COUNTRYT => $d->get('Country'));
  $template->param(EMAIL1 => $d->get('Email'));
  $template->param(EMAIL2 => $d->get('Confirm Email'));
  $template->param(FEMAIL => $d->get("Please try to avoid using a free email account(Ex: yahoo.com, hotmail.com, etc)"));
  $template->param(PAYINFO => $d->get('Payment Information'));
  $template->param(CARDTYPE => $d->get('Card Type'));
  $template->param(CARDNUMBER => $d->get('Credit Card Number'));
  $template->param(EXPDATE => $d->get('Expiration Date'));
  $template->param(CCVT => $d->get('CVV2 (3 digits on back of credit card)'));
  $template->param(REFUNDP => $d->get('Refund Policy'));
  $template->param(IAGREE => $d->get('I agree'));
  $template->param(NOAGREE => $d->get('I disagree'));

  
  $template->param(SUML => $d->get('Store Updates Mailing List'));
  $template->param(ASUML => $d->get("Yes! Add me to this store's mail list."));
  $template->param(SUBORDER => $d->get('Submit Order'));
  $template->param(PRIVACYPOLICY => $d->get('Privacy Policy'));
  my $temp = $d->get('After clicking the "Submit Order" button please be patient while your order is processed.\n
Your order can take up to 3 minutes.');


  $temp =~ s/\\//g;
  $temp =~ s/\n//;
  $template->param('ACSUBORDER' => $temp);
  $temp = $d->get('DO NOT press the "Submit Order" button more than once.');
  $temp =~ s/\\//g;
  
  $template->param(DNPSUBORDER => $temp);
  $template->param(ACDT => $d->get('All clips purchased are distributed through '));
  $temp = $d->get('%s uses 128Bit SSL Technology');
  $temp =~ s/\%s//;
  $template->param(SSLT => $temp);



  


}