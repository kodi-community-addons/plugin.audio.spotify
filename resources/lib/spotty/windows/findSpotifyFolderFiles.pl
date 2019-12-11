use strict;

use File::Basename qw(basename);
use File::Next;
use File::Slurp qw(read_file);
use File::Spec::Functions qw(catdir catfile);
use LWP::UserAgent;
use HTTP::Request;
use HTTP::Request::Common;
use Win32;

use constant MAX_FILE_TO_PARSE => 512 * 1024;

my $folder = catdir(Win32::GetFolderPath(Win32::CSIDL_LOCAL_APPDATA), 'Spotify', 'Storage');
my $candidates;

if (-d $folder && -r _) {
    my $files = File::Next::files({
        file_filter => sub {
            return -s $File::Next::name < MAX_FILE_TO_PARSE && /\.file$/;
        }
    }, $folder);

    while ( defined (my $file = $files->()) ) {
        my $data = read_file($file, scalar_ref => 1);
        if ($$data =~ /\bstart-group\b/) {
            push @$candidates, $file;
        }
    }
}

my $server = $ARGV[0];
$server = undef if $server !~ /:\d+$/;

foreach (@$candidates) {
    if ($server) {
        my $url = sprintf('http://%s/plugins/spotty/uploadPlaylistFolderData', $server);
        my $ua = LWP::UserAgent->new();
        my $response = $ua->post(
            $url,
            Content_Type => 'multipart/form-data', 
            Content => [filename => [$_, basename($_)]]
        );
        print $response->content;
    }
    else {
        print "$_\n";
    }
}

